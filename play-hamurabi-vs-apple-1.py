#!/usr/bin/env python3
# std
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
import blessed
import serial
import tqdm

def lf_to_cr(s): return s.replace('\n', '\r')
def cr_to_lf(s): return s.replace('\r', '\n')

# This program connects to an Apple-1 over serial,
# prompts the user to reset the computer,
# detects the "WozMon" prompt, and inserts WozMon
# code for HAMURABI.BAS, then, runs it over and over,
# playing computer against computer


def main(repl=False):
    term = blessed.Terminal()
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
    with serial.Serial(serial_device, baudrate=2400, rtscts=0, timeout=1) as ser, term.cbreak():
        # any time opening the serial device, the computer does a soft reset, it won't accept
        # keyboard or serial input or provide video output until 2 seconds have elapsed.
        time.sleep(2)
        if not repl:
            print(term.move(0, 0) + term.clear())
            print('Reset computer now')
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
            send_echo(ser, 'RUN\r')
        play_game(ser, term)

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


def send_echo(ser, send_string: str):
    for send_byte in send_string.encode('ascii'):
        send_echo_byte(ser, bytes([send_byte]))

def send_code(ser):
   code_data = open('software/HAMMURABI.TXT').read()
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
MATCH_TURN_BEGIN = (rb'\r\rHAMURABI: I BEG TO REPORT TO YOU,\r'
                    rb'IN YEAR (?P<YEAR>[0-9]{1,2}), (?P<STARVED>[0-9]{1,2}) PEOPLE STARVED,\r'
                    rb'(?P<INFANTS>[0-9]{1,3}) CAME TO THE CITY.\r'
                    rb'(?P<HORRIBLE_PLAGUE>A HORRIBLE PLAGUE STRUCK!!!\r--- HALF THE POPULATION DIED ---\r)?'
                    rb'THE POPULATION IS NOW (?P<POPULATION>[0-9]{1,4})\r'
                    rb'THE CITY NOW OWNS (?P<ACRES>[0-9]{1,9}) ACRES.\r'
                    rb'YOU HARVESTED (?P<HARVESTED>[0-9]{1,9}) BUSHELS PER ACRE,\r'
                    rb'RATS ATE (?P<RATS_EATEN>[0-9]{1,5}) BUSHELS,\r'
                    rb'YOU NOW HAVE (?P<BUSHELS>[0-9]{1,8}) BUSHELS IN STORE.\r')
MATCH_TURN_BUY = (rb'\rLAND IS TRADING AT (?P<LAND_VALUE>[0-9]{1,2}) BUSHELS PER ACRE,\r'
                  rb'HOW MANY ACRES DO YOU WISH TO BUY?')
MATCH_TURN_SELL = b'\rHOW MANY ACRES DO YOU WISH TO SELL?'
MATCH_TURN_FEED = b'\rHOW MANY BUSHELS DO YOU WISH TO FEED YOUR PEOPLE?'
MATCH_TURN_PLANT = b'\rHOW MANY ACRES DO YOU WISH TO PLANT\rWITH SEED?'
MATCH_PEOPLE_STARVED = b'\rYOU STARVED (?P<STARVED_TOOMANY>[0-9]{1,4}) PEOPLE IN ONE YEAR!!!\r'

# IN YOUR 10 YEAR TERM OF OFFICE 0\r
# PERCENT OF THE POPULATION STARVED ON THE\r
# AVERAGE, I.E., A TOTAL OF 11 PEOPLE\r
# DIED!!!\r
# YOU STARTED WITH 10 ACRES PER PERSON \r
# AND ENDED WITH 9 ACRES\r
# PER PERSON.\r
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

#THINK_AGAIN = (b'\rHAMURABI: THINK AGAIN. YOU HAVE ONLY\r'
#               b'(?P<ACRES>[0-9]{1,9}) BUSHELS OF GRAIN. NOW THEN\r')

def play_game(ser, term):
    game_log = []
    with streamexpect.wrap(ser) as stream:
        while True:
            # XXX risk_multiplier, even at 1.5, a 1-acre harvest with some rats
            # can starve us, so we are a very conservative party, hoarding
            # plenty of grain and making aggressive trades in the land market.
            risk_multiplier = 2
            input_acres = 100
            final_starting_bushels = 2500
            population = 95
            plant_acres = 100
            buy_acres = 0
            sell_acres = 0
            feed_people = 0
            print('Waiting for game start')
            stream.expect_bytes(MATCH_GAME_BEGIN)
            lost = False
            total_rats_eaten = 0
            total_harvested = 0
            total_starved = 0
            total_infants = 0
            total_lost_to_plague = 0
            total_land_purchases = 0
            total_land_sales = 0
            for turn in range(1, 12):
                if turn == 10:
                    risk_multiplier = 1
                searcher = streamexpect.SearcherCollection(
                    streamexpect.RegexSearcher(MATCH_TURN_BEGIN),
                    streamexpect.RegexSearcher(MATCH_PEOPLE_STARVED),
                )
                match = stream.expect(searcher)
                match_values = {key: int(value.decode()) if value and value.decode().isdigit() else value
                                for key, value in match.groupdict.items()}
                if 'STARVED_TOOMANY' in match_values:
                    print(f"Game lost: starvation ({match_values['STARVED_TOOMANY']})")
                    lost = True
                    break
                print('='* 40)
                turn = match_values['YEAR']
                print(f'Year                   {turn}')
                print('='* 40)
                starting_population = population
                print(f'Starting population    {starting_population}')
                infants = match_values['INFANTS']
                if infants > 0:
                    print(f'                     + {infants} (infants)')
                    total_infants += infants
                starved = match_values['STARVED']
                if starved:
                    print(f'                     - {starved} (starved)')
                    total_starved += starved
                lost_to_plague = 0
                if match_values['HORRIBLE_PLAGUE']:
                    lost_to_plague = int(math.ceil((starting_population + infants - starved) / 2))
                    print(f'                     - {lost_to_plague} (plague)')
                    total_lost_to_plague += lost_to_plague
                population = match_values['POPULATION']
                print('                    ---------------')
                print(f'Ending population   => {population}')
                assert starting_population + infants - lost_to_plague - starved == population

                print()
                starting_acres = input_acres
                if buy_acres or sell_acres:
                    print(f'Starting acres         {starting_acres}')
                if sell_acres:
                    print(f'                     - {sell_acres}')
                    total_land_sales += sell_acres
                if buy_acres:
                    print(f'                     + {buy_acres}')
                    total_land_purchases += buy_acres
                if buy_acres or sell_acres:
                    print('                    ---------------')
                input_acres = match_values['ACRES']
                print(f'Ending acres        => {input_acres}')
                if buy_acres or sell_acres:
                    assert input_acres == starting_acres + buy_acres - sell_acres

                print()
                wealth = input_acres / population
                print(f'Wealth              => {wealth:2.1f}')

                harvested = match_values['HARVESTED']
                total_harvested += harvested
                if turn != 1:
                    print()
                    print(f'Starting bushels       {final_starting_bushels}')
                input_bushels = match_values['BUSHELS']
                if turn != 1:
                    rats_eaten = match_values['RATS_EATEN']
                    if feed_people:
                        print(f'                     - {feed_people} (food)')
                    if plant_acres:
                        print(f'                     - {plant_acres // 2} (plant)')
                    if rats_eaten:
                        print(f'                     - {rats_eaten} (rats)')
                        total_rats_eaten += rats_eaten
                    print(f'                     + {harvested * plant_acres} ({harvested} harvested per acre)')
                    print('                    ---------------')
                    assert input_bushels == (final_starting_bushels
                                             - rats_eaten
                                             - feed_people
                                             - (plant_acres // 2)
                                             + (harvested * plant_acres))
                print(f'Ending bushels      => {input_bushels}')

                if turn == 11:
                    break

                match = stream.expect_regex(MATCH_TURN_BUY)
                acres_cost = int(match.groupdict['LAND_VALUE'])
                print()
                print(f'Land Value          => {acres_cost} (per acre)')

                sell_acres = calc_land_sales(population=population, given_bushels=input_bushels,
                                             acres=input_acres, acres_cost=acres_cost,
                                             turn=turn, risk_multiplier=risk_multiplier)
                buy_acres = 0
                if sell_acres == 0:
                    buy_acres = calc_land_purchases(population=population, given_bushels=input_bushels + (sell_acres * acres_cost),
                                                    acres=input_acres - sell_acres,
                                                    acres_cost=acres_cost, turn=turn, risk_multiplier=risk_multiplier)
                final_acres = input_acres - sell_acres + buy_acres

                final_starting_bushels = input_bushels + (sell_acres * acres_cost) - (buy_acres * acres_cost)

                # We can win the game while starving up to 3% of the population !
                starve_people = int(math.ceil(population * .03))
                feed_people = min((population - starve_people) * 20, final_starting_bushels)

                plant_acres = min(final_acres, population * 10, final_starting_bushels - feed_people)

                possible_values = []
                bushels_allocated = feed_people + (plant_acres // 2)
                for bushel_per_acre_harvested in range(1, 6):
                    _harvested = (bushel_per_acre_harvested * plant_acres)
                    # rats can eat 0, 1/2, or 1/4 of available food
                    for rats_multiplier in (.5, .75, 1):
                        _eaten = int(math.ceil((final_starting_bushels - feed_people - plant_acres) * rats_multiplier))
                        possible_values.append(final_starting_bushels - _eaten + _harvested)
                possible_values.sort()
                print()
                print(' => Buy ' + str(buy_acres) + ' acres of land')
                send_echo(ser, f'{buy_acres}\r')
                if buy_acres == 0:
                    # when buying '0' acres, expect prompt to sell
                    print(' => Sell ' + str(sell_acres) + ' acres of land')
                    stream.expect_bytes(MATCH_TURN_SELL)
                    send_echo(ser, f'{sell_acres}\r')

                print(f' => Feed your people {feed_people} bushels of grain')
                stream.expect_bytes(MATCH_TURN_FEED)
                send_echo(ser, f'{feed_people}\r')

                print(f' => Plant {plant_acres} acres of land with grain')
                stream.expect_bytes(MATCH_TURN_PLANT)
                send_echo(ser, f'{plant_acres}\r')

                print(f' ** risk_multiplier={risk_multiplier}, bushels_allocated={bushels_allocated}')
                print(f' ** Possible bushels next turn: {possible_values}')
                print()

            game_record = {}
            final_score = 0
            if not lost:
                print('Waiting for game end')
                match = stream.expect_regex(MATCH_LAST_TURN)
                game_record.update({key.lower(): int(value) for key, value in match.groupdict.items()})
                match = stream.expect_regex(MATCH_END_RATINGS)
                # todo change to dict
                for check_score, check_pattern in (
                        (0, MATCH_NATIONAL_FINK),
                        (1, MATCH_UNPLEASANT),
                        (2, MATCH_NOT_TOO_BAD),
                        (3, MATCH_FANTASTIC)):
                    # just check first 20 chars, this is a bit of a cheat ..
                    # maybe better to use PNAME or something?
                    if check_pattern[:20] in match.match:
                        final_score = check_score
                        break
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
                print('We Lost :(')
                print('Press any key for another game ...')
                term.inkey()

            send_echo(ser, 'RUN\r')


def calculate_grain_target(population, acres, risk_multiplier, turn):
    # let us calculate, how much food is needed to survive
    # in the worst-case scenario, that only 1 bushel per acre is harvested
    # and that rats eat 1/2 of what is in store, how much food is needed
    # to feed our population and plant our fields in such case?
    grain_needed = population * 20 + (acres // 2)
    if turn == 10:
        given_bad_harvest = 0
        given_rats_multiplier = 1
    else:
        given_bad_harvest = (acres * 1)
        given_rats_multiplier = risk_multiplier
    return (grain_needed // given_rats_multiplier) + given_bad_harvest


def calc_land_sales(population, given_bushels, acres, acres_cost, turn, risk_multiplier):
    # we want to reserve the full acres that may be planted
    can_plant_acres = population * 10
    # aim to increment wealth by 1 for each turn, so that by turn 7 we are "wealthy"
    # for end game, maybe could be linear to final turn (10)
    min_wealth = turn
    sell_acres = 0
    for sell_acres in range(0, acres):
        bushels = given_bushels + (acres_cost * sell_acres)
        grain_needed = calculate_grain_target(population, acres - sell_acres, risk_multiplier, turn)
        surplus = bushels - grain_needed
        wealth = (acres - sell_acres) / population
        disp_message = (f'sell_acres={sell_acres}? grain_needed={grain_needed}, bushels={bushels}, surplus={surplus}, wealth={wealth:2.2f}:')
        # no need to sell land if there is a surplus of food.
        if surplus > grain_needed:
            print(disp_message + ' surplus exceeded!')
            break
        if wealth < min_wealth:
            # it is more important to sell enough land to feed our people than for them to be wealthy,
            # we may have to sell land when there is a shortfall of food when risk_multiplier != 0
            print(disp_message + ' too unwealthy!')
            break


    return max(0, sell_acres - 1)

def calc_land_purchases(population, given_bushels, acres, acres_cost, turn, risk_multiplier):
    can_plant_acres = population * 10
    for buy_acres in range(0, acres):
        bushels = given_bushels - (acres_cost * buy_acres)
        grain_needed = calculate_grain_target(population, acres + buy_acres, risk_multiplier, turn)
        surplus = bushels - (buy_acres * acres_cost) - grain_needed
        wealth = (acres + buy_acres) / population
        disp_message = (f'buy_acres={buy_acres}? grain_needed={grain_needed}, bushels={bushels}, surplus={surplus}, wealth={wealth:2.2f}:')
        # cannot buy land unless there is a surplus.
        if risk_multiplier == 1:
            if surplus < 0:
                print(disp_message + ' surplus target met! (surplus<0)')
                break
        elif risk_multiplier == 1.5:
            if surplus < (grain_needed / 4):
                print(disp_message + ' surplus target met! (surplus<grain_needed/4)')
                break
        elif risk_multiplier == 2:
            if surplus < (grain_needed / 2):
                print(disp_message + ' surplus target met (surplus<grain_needed/2)!')
                break

        # we can only plant 10 acres per person
        if (acres + buy_acres) > can_plant_acres:
            print(disp_message + ' not enough farmers!')
            break

        if wealth > 12:
            print(disp_message + 'already too wealthy!')
            break
    return max(0, buy_acres - 1)


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


# streamexpect.ExpectTimeout: b'SH TO FEED YOUR PEOPLE?\rHOW MANY ACRES DO YOU WISH TO PLANT\rWITH SEED?\r\rHAMURABI: I BEG TO REPORT TO YOU,\rIN YEAR 10, 3 PEOPLE STARVED,\r10 CAME TO THE CITY.\rTHE POPULATION IS NOW 82\rTHE CITY NOW OWNS 616 ACRES.\rYOU HARVESTED 5 BUSHELS PER ACRE,\rRATS ATE 0 BUSHELS,\rYOU NOW HAVE 3603 BUSHELS IN STORE.\r\rLAND IS TRADING AT 25 BUSHELS PER ACRE,\rHOW MANY ACRES DO YOU WISH TO BUY?\r\rHOW MANY BUSHELS DO YOU WISH TO FEED YOUR PEOPLE?\rHOW MANY ACRES DO YOU WISH TO PLANT\rWITH SEED?\r\rHAMURABI: I BEG TO REPORT TO YOU,\rIN YEAR 11, 3 PEOPLE STARVED,\r9 CAME TO THE CITY.\rTHE POPULATION IS NOW 88\rTHE CITY NOW OWNS 648 ACRES.\rYOU HARVESTED 5 BUSHELS PER ACRE,\rRATS ATE 179 BUSHELS,\rYOU NOW HAVE 3960 BUSHELS IN STORE.\r\rIN YOUR 10 YEAR TERM OF OFFICE 4\rPERCENT OF THE POPULATION STARVED ON THE\rAVERAGE, I.E., A TOTAL OF 67 PEOPLE\rDIED!!!\rYOU STARTED WITH 10 ACRES PER PERSON \rAND ENDED WITH 7 ACRES\rPER PERSON.\r\rA LOUSY PERFORMANCE!!!\rTHE PEOPLE (REMAINING) FIND YOU AN\rUNPLEASANT RULER, AND FRANKLY \rHATE YOUR GUTS!!!\rSO LONG FOR NOW\r\r>'
