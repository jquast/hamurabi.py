#!/usr/bin/env python3
# std
import functools
import dataclasses
import datetime
import glob
import sys
import time
import math
import csv
import re

# 3rd
import simple_term_menu
import streamexpect
import tabulate
import blessed
import serial
import tqdm
import pyte

def lf_to_cr(s): return s.replace('\n', '\r')
def cr_to_lf(s): return s.replace('\r', '\n')

# This program connects to an Apple-1 over serial,
# prompts the user to reset the computer,
# detects the "WozMon" prompt, and inserts WozMon
# code for HAMURABI.BAS, then, runs it over and over,
# playing computer against computer

WINDOW_Y_TOP = 8
WINDOW_X_LEFT = 25

@dataclasses.dataclass
class DataTableItem:
    turn: int
    wealth: int
    pop: int
    infants: int
    starved: int
    plague: int
    acres: int
    change: int
    harvested: int
    feed: int
    rats: int
    planted: int

def main(repl=False):
    term = blessed.Terminal()
    window_calc = pyte.Screen(40, 24)
    stream_calc = pyte.Stream(window_calc)
    window_game = pyte.Screen(40, 24)
    stream_game = pyte.Stream(window_game)
    assert term.width >= 134
    assert term.height >= 49

    def print_window(text, window, stream, x, color='bright_red'):
        term_attr = getattr(term, color)
        if isinstance(text, bytes):
            text = text.decode()
        stream.feed(term_attr(text.replace('\r', '\r\n')))
        for y in window.dirty:
            for inner_x in range(window.columns):
                char = window.buffer[y][inner_x]
                if char.fg == 'default':
                    term_attr = str
                else:
                    term_attr = term.color_rgb(int(char.fg[0:2], 16), int(char.fg[2:4], 16), int(char.fg[4:6], 16))
                print(term.move_yx(y + WINDOW_Y_TOP, x + inner_x) + term_attr(char.data) or ' ', end='', flush=True)
                
    print_calc = functools.partial(print_window, window=window_calc, stream=stream_calc, x=2 + WINDOW_X_LEFT, color='darkolivegreen3')
    print_game = functools.partial(print_window, window=window_game, stream=stream_game, x=45 + WINDOW_X_LEFT)
    output = ''
    devices = glob.glob('/dev/cu.*')
    if len(devices) < 1:
        print("No serial devices found!")
        exit(1)
    elif len(devices) == 1:
        serial_device = devices[0]
    else:
        terminal_menu = simple_term_menu.TerminalMenu(devices, title="Select a serial device")
        menu_entry_index = terminal_menu.show()
        if menu_entry_index is None:
            print("You have selected to exit!")
            exit(0)
        serial_device = devices[menu_entry_index]

#    def fn_echo(text, color='chocolate'):
#        term_attr = getattr(term, color)
#        print(term_attr(text.decode().replace('\r', '\n')), end='', flush=True)

    with serial.Serial(serial_device, baudrate=2400, rtscts=0, timeout=2) as ser, term.cbreak():
        # any time opening the serial device, the computer does a soft reset, it won't accept
        # keyboard or serial input or provide video output until 2 seconds have elapsed.
        print(term.move(0, 0) + term.clear())
        time.sleep(2)
        if not repl:
            print('Reset computer now, press any key')
            result = ''
            while True:
                result += ser.read(10).decode()
                if result.endswith('\\\r'):
                    break
            recv_char = ser.read(1).decode()
            print('Reset detected, sending HAMURABI.BAS ...')
            send_code(ser)
            print('Code loaded successfully!')
        else:
            ser.write(b'\r\r')
            time.sleep(1)
            send_echo(ser, print_game, 'RUN\r')
        play_game(ser, term, print_calc, print_game)

def send_echo_byte(ser, send_byte: bytes):
    assert len(send_byte) == 1, send_byte
    ser.write(send_byte)
    while True:
        recv_byte = ser.read(1)
        if send_byte != b'\r':
            if send_byte == recv_byte:
                return recv_byte
            # read next character? sometimes it looks like
            # streamexpect pushes ahead?
            continue
        return recv_byte


def send_echo(ser, printer: callable, send_string: str):
    for send_byte in send_string.encode('ascii'):
        send_echo_byte(ser, bytes([send_byte]))
        # transpose for local tty output
#        if send_byte == '\r':
#            send_byte = '\r'
        printer(bytes([send_byte]).decode(), color='gold')

def send_code(ser):
   code_data = open('apple1-HAMMURABI.TXT').read()
   in_basic = False
   # this is a wozmon insert sequence, send one byte at a time, awaiting echo back from the apple-1
   # serial port, to ensure not to overrun the max232 chip, which has no flow control
   with tqdm.tqdm(total=len(code_data), unit='B', unit_scale=True, unit_divisor=1024) as pbar:
       bytes_sent = 0
       for code_line in code_data.splitlines():
           for send_byte in (code_line + '\r').encode('ascii'):
               bytes_sent += 1
               pbar.update(1)
               send_echo_byte(ser, bytes([send_byte]))

           # did we perform a jump address? we must be in basic, now
           if re.match(r'[0-9A-F]{4}R', code_line):
               in_basic = True

           # after any wozmon command, jump address or memory insert, await the echo
           # back of wozmon's display of first address byte, this causes the transfer
           # to go really slow, though ! experiments in variant without echo back
           if re.match(r'([0-9A-F]{4}R|[0-9A-F]{4}: [0-9A-F]{2})', code_line):
               result = ''
               maybe_prompt = '>' if in_basic else ''
               while True:
                   result += ser.read(1).decode()
                   if re.match(rf'\r([0-9A-F]{{4}}: [0-9A-F]{{2}})\r{maybe_prompt}$', result):
                       break

           # if we are in basic and a newline is sent, expect newline + prompt in return
           if in_basic and code_line == '':
               assert ser.read(2) == b'\r>'
       print('Code load completed successfully!')

MATCH_GAME_BEGIN = b'\r\rTRY YOUR HAND AT GOVERNING ANCIENT\rSUMERIA SUCCESSFULLY FOR A 10-YEAR TERM\rOF OFFICE.\r'
MATCH_TURN_BEGIN = (rb'\rHAMURABI: I BEG TO REPORT TO YOU,\r'
                    rb'IN YEAR (?P<YEAR>[0-9]{1,2}), (?P<STARVED>[0-9]{1,2}) PEOPLE STARVED,\r'
                    rb'(?P<INFANTS>[0-9]{1,3}) CAME TO THE CITY.\r'
                    rb'(?P<HORRIBLE_PLAGUE>A HORRIBLE PLAGUE STRUCK!!!\r--- HALF THE POPULATION DIED ---\r)?'
                    rb'THE POPULATION IS NOW (?P<POPULATION>[0-9]{1,4})\r'
                    rb'THE CITY NOW OWNS (?P<ACRES>[0-9]{1,9}) ACRES.\r'
                    rb'YOU HARVESTED (?P<HARVESTED>[0-9]) BUSHELS PER ACRE,\r'
                    rb'RATS ATE (?P<RATS_EATEN>[0-9]{1,5}) BUSHELS,\r'
                    rb'YOU NOW HAVE (?P<BUSHELS>[0-9]{1,8}) BUSHELS IN STORE.\r')
MATCH_TURN_BUY = (rb'\rLAND IS TRADING AT (?P<LAND_VALUE>[0-9]{1,2}) BUSHELS PER ACRE,\r'
                  rb'HOW MANY ACRES DO YOU WISH TO BUY?')
MATCH_TURN_SELL = b'\rHOW MANY ACRES DO YOU WISH TO SELL?'
MATCH_TURN_FEED = b'\rHOW MANY BUSHELS DO YOU WISH TO FEED YOUR PEOPLE?'
MATCH_TURN_PLANT = b'\rHOW MANY ACRES DO YOU WISH TO PLANT\rWITH SEED?'
MATCH_PEOPLE_STARVED = b'\rYOU STARVED (?P<STARVED_TOOMANY>[0-9]{1,4}) PEOPLE IN ONE YEAR!!!\r'
MATCH_LAST_TURN = (rb'\rIN YOUR 10 YEAR TERM OF OFFICE (?P<PCT_STARVED>[0-9]{1,3})\r'
                   rb'PERCENT OF THE POPULATION STARVED ON THE\r'
                   rb'AVERAGE, I.E., A TOTAL OF (?P<TOTAL_DEATHS>[0-9]{1,4}) PEOPLE\r'
                   rb'DIED!!!\r'
                   rb'YOU STARTED WITH 10 ACRES PER PERSON \r'
                   rb'AND ENDED WITH (?P<WEALTH>[0-9]{1,4}) ACRES\r'
                   rb'PER PERSON.\r')
MATCH_NATIONAL_FINK = (b'DUE TO THIS EXTREME MISMANAGEMENT YOU\r'
                       b'HAVE NOT ONLY BEEN IMPEACHED AND THROWN\r'
                       b'OUT OF OFFICE BUT YOU HAVE ALSO BEEN\r'
                       b"DECLARED 'NATIONAL FINK'!!!")
MATCH_FANTASTIC = (b'A FANTASTIC PERFORMANCE!!!\r'
                   b'CHARLEMANGE,DISRAELI, AND JEFFERSON\r'
                   b'COMBINED COULD NOT HAVE DONE BETTER!')
MATCH_UNPLEASANT = (b'A LOUSY PERFORMANCE!!!\r'
                    rb'THE PEOPLE \(REMAINING\) FIND YOU AN\r'
                    b'UNPLEASANT RULER, AND FRANKLY \r'
                    b'HATE YOUR GUTS!!!')
MATCH_NOT_TOO_BAD = (b'YOUR PERFORMANCE COULD HAVE BEEN BETTER\r'
                     b"BUT WASN'T TOO BAD, [0-9]{1,5} PEOPLE WOULD \r"
                     b'LOVE TO SEE YOU ASSASSINATED.')
MATCH_END_RATINGS = f'({MATCH_NATIONAL_FINK.decode()}|{MATCH_FANTASTIC.decode()}|{MATCH_UNPLEASANT.decode()}|{MATCH_NOT_TOO_BAD.decode()})'.encode()


MATCH_END_GAME = b"\rSO LONG FOR NOW"



def play_game(ser, term, print_calc, print_game):
    game_log = []

    lines = tabulate.tabulate([["x" * 40, "z"*40]]*24, tablefmt='rounded_outline').splitlines()
    for y, line in enumerate(lines):
        print(term.move_yx(y=WINDOW_Y_TOP + y - 1, x=WINDOW_X_LEFT) + line)

    with streamexpect.wrap(ser, fn_echo=functools.partial(print_game, color='chocolate')) as stream:
        while True:
            input_acres = 1000
            plant_acres = 1000
            harvested = 3
            previous_starting_bushels = 0
            final_starting_bushels = 2800
            population = 95
            buy_acres = 0
            sell_acres = 0
            feed_people = 0
            rats_eaten = 200
            #next_turn_bushels = [2800]
            lost = False
            total_rats_eaten = 0
            total_harvested = 0
            total_starved = 0
            total_infants = 0
            total_lost_to_plague = 0
            total_land_purchases = 0
            total_land_sales = 0
            acres_cost = 0

            print_calc('Ready ...\r')
            stream.expect_bytes(MATCH_GAME_BEGIN)

            data_table = []
            with open('game_log.csv', 'r') as f:
                reader = csv.DictReader(f)
                games = [row['final_score'] for row in reader]
                total_games = len(games)
                games_3 = games.count('3')
                games_2 = games.count('2')
                games_1 = games.count('1')
                games_0 = games.count('0')
                headers = ['total games', 'best', 'good', 'ok', 'lost']
                table_data = [
                    [f'{total_games:,}', f'{games_3:,}', f'{games_2:,}', f'{games_1:,}', f'{games_0:,}'],
                    ['pct.',
                     (f'{(games_3/total_games)*100:2.1f}' if games_3 else '0') + '%',
                     (f'{(games_2/total_games)*100:2.1f}' if games_2 else '0') + '%',
                     (f'{(games_1/total_games)*100:2.1f}' if games_1 else '0') + '%',
                     (f'{(games_0/total_games)*100:2.1f}' if games_0 else '0') + '%',]]

                lines = tabulate.tabulate(table_data, tablefmt='rounded_outline', stralign='right', headers=headers).splitlines()
                for y, line in enumerate(lines):
                    print(term.move_yx(y=y, x=WINDOW_X_LEFT + 15) + line)

            for turn in range(1, 12):
                searcher = streamexpect.SearcherCollection(
                    streamexpect.RegexSearcher(MATCH_TURN_BEGIN),
                    streamexpect.RegexSearcher(MATCH_PEOPLE_STARVED),
                )
                match = stream.expect(searcher, timeout=10)
                if match is None:
                    raise TimeoutError('Timeout in MATCH_TURN_BEGIN')
                match_values = {key: int(value.decode()) if value and value.decode().isdigit() else value
                                for key, value in match.groupdict.items()}
                if 'STARVED_TOOMANY' in match_values:
                    print_calc(f"Game lost: starvation ({match_values['STARVED_TOOMANY']})\r")
                    lost = True
                    break

                turn = match_values['YEAR']
                starting_population = population
                infants = match_values['INFANTS']
                total_infants += infants
                starved = match_values['STARVED']
                total_starved += starved

                lost_to_plague = 0
                if match_values['HORRIBLE_PLAGUE']:
                    lost_to_plague = int(math.ceil((starting_population + infants - starved) / 2))
                total_lost_to_plague += lost_to_plague
                population = match_values['POPULATION']
                assert starting_population + infants - lost_to_plague - starved == population

                starting_acres = input_acres
                total_land_sales += sell_acres
                total_land_purchases += buy_acres
                input_acres = match_values['ACRES']
                wealth = input_acres / population
                assert input_acres == starting_acres + buy_acres - sell_acres

                harvested = match_values['HARVESTED']
                total_harvested += harvested
                input_bushels = match_values['BUSHELS']
                rats_eaten = match_values['RATS_EATEN']
                total_rats_eaten += rats_eaten
                if turn == 1:
                    assert input_bushels == (
                        (harvested * plant_acres)
                        - rats_eaten)
                else:
                    assert input_bushels == (final_starting_bushels
                                                - rats_eaten
                                                - feed_people
                                                - (plant_acres // 2)
                                                + (harvested * plant_acres))

                print_calc('\r\r\r' + '='* 40 + '\r')
                print_calc(f'Year                   {turn}\r')
                print_calc('='* 40)
                print_calc(f'Starting population    {starting_population}\r')
                if infants > 0:
                    print_calc(f'                     + {infants} (infants)\r')
                if starved:
                    print_calc(f'                     - {starved} (starved)\r')
                if lost_to_plague:
                    print_calc(f'                     - {lost_to_plague} (plague)\r')
                print_calc('                    ---------------\r')
                print_calc(f'Ending population   => {population}\r')
                if buy_acres or sell_acres:
                    print_calc('\r')
                    print_calc(f'Starting acres         {starting_acres}\r')
                if sell_acres:
                    print_calc(f'                     - {sell_acres} (sold)\r')
                if buy_acres:
                    print_calc(f'                     + {buy_acres} (bought)\r')
                if buy_acres or sell_acres:
                    print_calc('                    ---------------\r')
                print_calc(f'Ending acres        => {input_acres}\r')
                print_calc(f'Wealth              => {wealth:2.1f}\r')
                print_calc('')
                print_calc(f'Food BEGIN =>  {previous_starting_bushels}\r')
                if sell_acres:
                    print_calc(f'             + {sell_acres * acres_cost} (land sale)\r')
                if buy_acres:
                    print_calc(f'             - {buy_acres * acres_cost} (land purchase)\r')
                if feed_people:
                    print_calc(f'             - {feed_people} (food)\r')
                if plant_acres:
                    print_calc(f'             - {plant_acres // 2} (planted)\r')
                if turn != 1:
                    food_in_store = previous_starting_bushels + (sell_acres * acres_cost) - (buy_acres * acres_cost) - feed_people - (plant_acres // 2)
                    print_calc(f'In STORE   =>  {food_in_store}\r')
                if rats_eaten:
                    print_calc(f'             - {rats_eaten} (rats eaten)\r')
                print_calc(f'             + {harvested * plant_acres} ({harvested}/acre)\r')
                print_calc('            ---------------\r')
                print_calc(f'Food END   =>  {input_bushels}\r')

                if turn == 11:
                    break

                match = stream.expect_regex(MATCH_TURN_BUY)
                acres_cost = int(match.groupdict['LAND_VALUE'])
                print_calc(f'Land Value => {acres_cost} (per acre)\r')

                # calculate land sales
                sell_acres = calc_land_sales(population=population, given_bushels=input_bushels,
                                             acres=input_acres, acres_cost=acres_cost,
                                             turn=turn)

                # calculate land purchases
                buy_acres = 0
                if sell_acres == 0:
                    buy_acres = calc_land_purchases(population=population, given_bushels=input_bushels + (sell_acres * acres_cost),
                                                    acres=input_acres - sell_acres,
                                                    acres_cost=acres_cost, turn=turn)

                previous_starting_bushels = input_bushels # final_starting_bushels
                final_starting_bushels = input_bushels + (sell_acres * acres_cost) - (buy_acres * acres_cost)
                final_acres = input_acres - sell_acres + buy_acres
                # TODO: if plant_acres < final_acres, then, we should 0 out our buys and sell acres that we cannot plant!
                plant_acres, feed_people = determine_food_distribution(final_starting_bushels, population, final_acres, turn)
                #next_turn_bushels = predict_next_turn_bushels(final_starting_bushels, plant_acres, feed_people)

                # print_calc(f'Will buy {buy_acres} of land, sell {sell_acres}, feed {feed_people}, and plant {plant_acres} acres.\r')

                data_table.append(DataTableItem(
                    turn=turn,
                    wealth=f'{wealth:2.1f}',
                    pop=f'{population:,}',
                    infants=f'+{infants:,}',
                    plague=f'{lost_to_plague*-1:,}',
                    starved=f'{starved*-1:,}',
                    acres=f'{input_acres:,}',
                    change=f'+{buy_acres}' if buy_acres else sell_acres * -1,
                    harvested=f'+{harvested * plant_acres:,}',
                    planted=f'{(plant_acres // 2) * -1:,}',
                    feed=f'{feed_people * -1:,}',
                    rats=f'{rats_eaten*-1:,}',
                    ))

                with term.location(y=WINDOW_Y_TOP + 26, x=0):
                    print(tabulate.tabulate(data_table, tablefmt='rounded_outline', headers='keys', stralign='right'), end='')
                    print(term.clear_eos, end='', flush=True)


                send_echo(ser, print_game, f'{buy_acres}\r')
                if buy_acres == 0:
                    # when buying '0' acres, expect prompt to sell
                    stream.expect_bytes(MATCH_TURN_SELL)
                    send_echo(ser, print_game, f'{sell_acres}\r')

                stream.expect_bytes(MATCH_TURN_FEED)
                send_echo(ser, print_game, f'{feed_people}\r')

                stream.expect_bytes(MATCH_TURN_PLANT)
                send_echo(ser, print_game, f'{plant_acres}\r')

            game_record = {}
            final_score = 0
            if not lost:
                print_calc('Waiting for game end\r')
                match = stream.expect_regex(MATCH_LAST_TURN)
                game_record.update({key.lower(): int(value) for key, value in match.groupdict.items()})
                final_score = determine_final_score(stream)
            lost = lost or (final_score == 0)
            stream.expect_bytes(MATCH_END_GAME)
            game_record.update({
                'datetime': datetime.datetime.now(),
                'population': population,
                'bushels': input_bushels,
                'wealth': wealth,
                'acres': input_acres,
                'last_turn': turn,
                'total_harvested': total_harvested,
                'total_rats_eaten': total_rats_eaten,
                'total_starved': total_starved,
                'total_infants': total_infants,
                'total_lost_to_plague': total_lost_to_plague,
                'total_land_purchases': total_land_purchases,
                'total_land_sales': total_land_sales,
                'final_score': final_score
            })
            save_game_log(game_record)
            stream.expect_bytes(b'>')
            if lost:
                print_calc('We Lost :(\r')

            send_echo(ser, print_game, 'RUN\r')

def determine_food_distribution(final_starting_bushels, population, final_acres, turn):
    # we can always starve 3% of our population without reprocussion !
    starve_people = (population * .03).__ceil__()

    for _ in range(starve_people, population - starve_people):
        grain_needed = calculate_grain_starved(population, starve_people, final_acres, turn)
        
        # how many people can we starve?
        feed_people = (population - starve_people) * 20
        surplus = final_starting_bushels - grain_needed
        disp_message = (f'surplus<{surplus}> = final_starting_bushels<{final_starting_bushels}> '
                        f'- grain_needed<{grain_needed}>: ')

        # starvation limit is 45% for the microsoft basic port, but
        # for the integer basic (Apple 1) version, we calculate against
        # an upscaled formula:
        #     D=P-C: IF 10*d>4*P THEN 560
        if 10 * starve_people >= 4 * population:
            # print_calc(disp_message + f'starvation limit reached.\r')
            starve_people -= 1
            break

        if surplus > 0:
            # print_calc(disp_message + f'surplus met.\r')
            break

        if final_starting_bushels - (feed_people // 2) < 0:
            # print_calc(disp_message + f'GAME FAILURE PREDICTED!\r')
            break

        starve_people += 1
    
    feed_people = (population - starve_people) * 20
    plant_acres = 0 if turn == 10 else min(population * 10, final_acres, ((final_starting_bushels - feed_people) * 2) - 1)
    return plant_acres, feed_people

def calculate_grain_target(population, acres, turn):
    # let us calculate, how much food is needed to feed everyone and plant our fields,
    # we depend on the land we have "banked" for sale to reduce risk of starvation after
    # a season of low harvest and hungry rats ..
    # XXX TODO: carry in total population starvation and calculate more exactly
    starve_people = (population * .03).__ceil__()
    feed_population = (population - starve_people) * 20
    # print(f'? feed_population<{feed_population}> = ({population} - ({population} * .03).__ceil__()) * 20')
    if turn == 10:
        # leftover grain does not affect score, let the next ruler deal with it!
        return feed_population
    # how much grian we need to feed everyone and plant our fields.
    result = feed_population + (min(acres, population * 10) // 2) + 1
    # print(f'?-1 starve_people={starve_people}')
    # print(f'?-1 result<{result}> = feed_population<{feed_population}> + (min(acres<{acres}>, population<{population}> * 10) // 2)')
    # a BUG in the original game?!
    # --- 440 PRINT "HOW MANY ACRES DO YOU WISH TO PLANT WITH SEED";
    # --- 441 INPUT D:IF D=0 THEN 511
    # --- 442 IF D<0 THEN 850
    # should be,
    # --- 442 IF D<=0 THEN 850
    # we can't plant 1000 acres with 500 bushels of grain, we can only plant 999 acres !?
    # is this, leave 1 bushel for the king?! :)
    return result

def calculate_grain_starved(population, starve_people, acres, turn):
    # same as calculate_grain_target(), but for starving a specific amount of people
    # rather than 3%
    feed_population = (population - starve_people) * 20
    if turn == 10:
        return feed_population 
    result = feed_population + (min(acres, population * 10) // 2) + 1
    return result

def calc_land_sales(population, given_bushels, acres, acres_cost, turn):
    sell_acres = 0
    for sell_acres in range(0, acres + 1):
        #bushels = given_bushels + (acres_cost * sell_acres)
        grain_needed = calculate_grain_target(population, acres - sell_acres, turn)
        surplus = given_bushels + (sell_acres * acres_cost) - grain_needed 
        disp_message = f'sell_acres={sell_acres} ? surplus<{surplus}> = given_bushels<{given_bushels}> + (sell_acres<{sell_acres}> * acres_cost<{acres_cost}>) - grain_needed<{grain_needed}>: '
        # no need to sell land if there will be a surplus of food,
        # but, never end up with less land than we can reasonable plant,
        if surplus > 0:
            # print_calc(disp_message + f'surplus met.\r')
            break
    assert sell_acres < acres + 1, sell_acres
    return max(0, sell_acres)

def calc_land_purchases(population, given_bushels, acres, acres_cost, turn):
    # we aggressively buy land, because rats cannot eat land!
    MAX_BUY_ACRES = 999
    for buy_acres in range(0, MAX_BUY_ACRES + 2):
        grain_needed = calculate_grain_target(population, acres + buy_acres, turn)
        surplus = given_bushels - grain_needed - (buy_acres * acres_cost)
        disp_message = f'buy_acres={buy_acres} ? surplus<{surplus}> = given_bushels<{given_bushels} - grain_needed<{grain_needed}> - (buy_acres<{buy_acres}> * acres_cost<{acres_cost}>): '

        # only buy land when there is a surplus of grain.
        if surplus < 0:
            # print_calc(disp_message + f'surplus met.\r')
            buy_acres -= 1
            break
    assert buy_acres <= MAX_BUY_ACRES, buy_acres
    return max(0, buy_acres)

def determine_final_score(stream):
    match = stream.expect_regex(MATCH_END_RATINGS)
    for check_score, check_pattern in (
                        (0, MATCH_NATIONAL_FINK),
                        (1, MATCH_UNPLEASANT),
                        (2, MATCH_NOT_TOO_BAD),
                        (3, MATCH_FANTASTIC)):
        if check_pattern[:20] in match.match:
            return check_score
    assert False, ("Score unmatched", match.match)


def save_game_log(game_record):
    fieldnames = [
            'datetime', 'final_score', 'wealth', 'pct_starved', 'population', 'bushels', 'acres',
            'last_turn', 'total_deaths', 'total_harvested', 'total_rats_eaten', 'total_starved', 'total_infants',
            'total_lost_to_plague', 'total_land_purchases', 'total_land_sales']

    with open('game_log.csv', 'a') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if f.tell() == 0:
            writer.writeheader()
        writer.writerow(game_record)

if __name__ == '__main__':
    main(repl='--repl' in sys.argv)

# todo:
# - starvation can be increased to account for births, calculate "grand total"
# - do not sell acres for wealth below 7, this puts us in a losing situation,
#   better to starve up to 40% of population for better score
