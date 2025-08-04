#!/usr/bin/env python3
# std
import functools
import dataclasses
import datetime
import sys
import time
import math
import csv
import re
import subprocess

# 3rd
import tabulate
import blessed
import pexpect
import pyte

# This program runs a local hamurabi.py game and plays it automatically,
# running game after game and logging the results

WINDOW_Y_TOP = 8
WINDOW_X_LEFT = 25

@dataclasses.dataclass
class DataTableItem:
    turn: int
    wealth: float
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

def main():
    term = blessed.Terminal()
    window_calc = pyte.Screen(40, 24)
    stream_calc = pyte.Stream(window_calc)
    window_game = pyte.Screen(40, 24) 
    stream_game = pyte.Stream(window_game)
    # Relax terminal size requirements for testing
    # assert term.width >= 134
    # assert term.height >= 49

    def print_window(text, window, stream, x, color):
        term_attr = getattr(term, color)
        if isinstance(text, bytes):
            text = text.decode()
        stream.feed(term_attr(term_attr(text.replace('\n', '\r\n'))))
        for y in window.dirty:
            for inner_x in range(window.columns):
                char = window.buffer[y][inner_x]
                if char.fg == 'default':
                    term_attr = str
                else:
                    term_attr = term.color_rgb(int(char.fg[0:2], 16), int(char.fg[2:4], 16), int(char.fg[4:6], 16))
                print(term.move_yx(y + WINDOW_Y_TOP, x + inner_x) + term_attr(char.data) or ' ', end='', flush=True)
                
    print_calc = functools.partial(print_window, window=window_calc, stream=stream_calc, x=2 + WINDOW_X_LEFT, color='darkolivegreen3')
    print_game = functools.partial(print_window, window=window_game, stream=stream_game, x=45 + WINDOW_X_LEFT, color='orchid')

    print(term.move(0, 0) + term.clear())
    with term.cbreak():
        play_game(term, print_calc, print_game)

class GameOutputRedirector:
    """File-like object that redirects writes to the print_game function"""
    def __init__(self, print_func):
        self.print_func = print_func
    
    def write(self, data):
        if data:  # Only write if there's actual data
            self.print_func(data, color='gold')
        return len(data) if data else 0
    
    def flush(self):
        pass  # No-op for flush
    
    def close(self):
        pass  # No-op for close

def send_input(child, printer: callable, send_string: str):
    child.send(send_string)
    printer(send_string)

# Simpler patterns for Python hamurabi.py output
MATCH_YEAR_REPORT = r'In year (\d+), (\d+) people starved, (\d+) came to the city\.'
MATCH_PLAGUE = r'A horrible plague struck!! Half the people have perished\.'
MATCH_POPULATION = r'Population is now (\d+)'
MATCH_ACRES = r'The city now owns (\d+) acres\.'
MATCH_HARVESTED = r'You harvested (\d+) bushels per acre\.'
MATCH_RATS_EATEN = r'Rats have eaten (\d+) bushels from storage!'
MATCH_BUSHELS = r'You now have (\d+) bushels\.'
MATCH_LAND_VALUE = r'Land is trading at (\d+) bushels per acre\.'
MATCH_BUY_PROMPT = r'How many acres do you wish to buy \(0 to sell\)\?'
MATCH_SELL_PROMPT = r'How many acres do you wish to sell\?'
MATCH_FEED_PROMPT = r'How many bushels do you wish to feed your people\?'
MATCH_PLANT_PROMPT = r'How many acres do you wish to plant with seed\?'
MATCH_GAME_OVER = r'You starved (\d+) people in one year!!!'
MATCH_FINAL_REPORT = r'In your 10-year term of office, ([\d.]+)% of the population starved'
MATCH_FINAL_REPORT_DEATHS = r'words, (\d+) people DIED of starvation!!'
MATCH_FINAL_REPORT_NODEATHS = r'and nobody died of starvation!!'
MATCH_NATIONAL_FINK = r'Due to this extreme mismanagement\.'
MATCH_FANTASTIC = r'A fantastic performance\.'
MATCH_UNPLEASANT = r'Your heavy-handed performance'
MATCH_NOT_TOO_BAD = r'Your performance could have been'
MATCH_END_GAME = r'So long for now\.'

def play_game(term, print_calc, print_game):
    lines = tabulate.tabulate([["x" * 40, "z"*40]]*24, tablefmt='rounded_outline').splitlines()
    for y, line in enumerate(lines):
        print(term.move_yx(y=WINDOW_Y_TOP + y - 1, x=WINDOW_X_LEFT) + line)

    while True:
        # Start a new hamurabi.py process
        child = pexpect.spawn('python3 hamurabi.py', timeout=0.2)
        child.logfile_read = GameOutputRedirector(print_game)
        # child.logfile_read = sys.stdout.buffer

        
        # Game state variables
        input_acres = 1000
        plant_acres = 1000
        harvested = 3
        previous_starting_bushels = 0
        final_starting_bushels = 2800
        population = 95
        buy_acres = 0
        sell_acres = 0
        feed_people = 0
        rats_eaten = 0
        lost = False
        total_rats_eaten = 0
        total_harvested = 0
        total_starved = 0
        total_infants = 0
        total_lost_to_plague = 0
        total_land_purchases = 0
        total_land_sales = 0
        acres_cost = 0

        print_calc('Ready ...\r\n')
        
        data_table = []
        
        # Load and display game statistics
        try:
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
                     (f'{(games_0/total_games)*100:2.1f}' if games_0 else '0') + '%']]

                lines = tabulate.tabulate(table_data, tablefmt='rounded_outline', stralign='right', headers=headers).splitlines()
                for y, line in enumerate(lines):
                    print(term.move_yx(y=y, x=WINDOW_X_LEFT + 15) + line)
        except FileNotFoundError:
            pass

        try:
            for turn in range(1, 10):
                # Wait for turn report
                try:
                    child.expect(MATCH_YEAR_REPORT, timeout=0.1)
                    turn_match = child.match.groups()
                    
                    # Parse the match data
                    turn = int(turn_match[0])
                    starting_population = population
                    starved = int(turn_match[1])
                    infants = int(turn_match[2])
                    total_infants += infants
                    total_starved += starved
                    
                    # Check for plague
                    lost_to_plague = 0
                    try:
                        child.expect(MATCH_PLAGUE, timeout=0.1)
                        lost_to_plague = int(math.ceil((starting_population + infants - starved) / 2))
                    except pexpect.TIMEOUT:
                        pass
                    total_lost_to_plague += lost_to_plague
                    
                    # Get population
                    child.expect(MATCH_POPULATION, timeout=0.1)
                    population = int(child.match.group(1))
                    
                    # Get acres
                    child.expect(MATCH_ACRES, timeout=0.1)
                    input_acres = int(child.match.group(1))
                    wealth = input_acres / population if population > 0 else 0
                    
                    # Get harvest
                    child.expect(MATCH_HARVESTED, timeout=0.1)
                    harvested = int(child.match.group(1))
                    total_harvested += harvested
                    
                    # Check for rats (optional)
                    rats_eaten = 0
                    try:
                        child.expect(MATCH_RATS_EATEN, timeout=0.05)
                        rats_eaten = int(child.match.group(1))
                    except pexpect.TIMEOUT:
                        pass
                    total_rats_eaten += rats_eaten
                    
                    # Get bushels
                    child.expect(MATCH_BUSHELS, timeout=0.1)
                    input_bushels = int(child.match.group(1))

                except pexpect.TIMEOUT:
                    # Check if game ended due to starvation
                    try:
                        child.expect(MATCH_GAME_OVER, timeout=0.5)
                        starved_too_many = int(child.match.group(1))
                        print_calc(f"Game lost: starvation ({starved_too_many})\r\n")
                        lost = True
                        break
                    except pexpect.TIMEOUT:
                        print_calc("Timeout waiting for turn begin\r\n")
                        break

                # Display calculations
                print_calc('\r\n\r\n\r\n' + '='* 40 + '\r\n')
                print_calc(f'Year                   {turn}\r\n')
                print_calc('='* 40)
                print_calc(f'Starting population    {starting_population}\r\n')
                if infants > 0:
                    print_calc(f'                     + {infants} (infants)\r\n')
                if starved:
                    print_calc(f'                     - {starved} (starved)\r\n')
                if lost_to_plague:
                    print_calc(f'                     - {lost_to_plague} (plague)\r\n')
                print_calc('                    ---------------\r\n')
                print_calc(f'Ending population   => {population}\r\n')
                print_calc(f'Ending acres        => {input_acres}\r\n')
                print_calc(f'Wealth              => {wealth:2.1f}\r\n')
                print_calc(f'Food END   =>  {input_bushels}\r\n')

                if turn == 10:
                    break

                # Wait for land trading info
                child.expect(MATCH_LAND_VALUE, timeout=0.1)
                acres_cost = int(child.match.group(1))
                print_calc(f'Land Value => {acres_cost} (per acre)\r\n')

                # Calculate decisions
                sell_acres = calc_land_sales(population=population, given_bushels=input_bushels,
                                           acres=input_acres, acres_cost=acres_cost, turn=turn)

                buy_acres = 0
                if sell_acres == 0:
                    buy_acres = calc_land_purchases(population=population, 
                                                  given_bushels=input_bushels + (sell_acres * acres_cost),
                                                  acres=input_acres - sell_acres,
                                                  acres_cost=acres_cost, turn=turn)

                previous_starting_bushels = input_bushels
                final_starting_bushels = input_bushels + (sell_acres * acres_cost) - (buy_acres * acres_cost)
                final_acres = input_acres - sell_acres + buy_acres
                plant_acres, feed_people = determine_food_distribution(final_starting_bushels, population, final_acres, turn)

                # Update data table
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

                # Make moves
                child.expect(MATCH_BUY_PROMPT, timeout=0.1)
                send_input(child, print_game, f'{buy_acres}\n')
                
                if buy_acres == 0:
                    child.expect(MATCH_SELL_PROMPT, timeout=0.1)
                    send_input(child, print_game, f'{sell_acres}\n')

                child.expect(MATCH_FEED_PROMPT, timeout=0.1)
                send_input(child, print_game, f'{feed_people}\n')

                child.expect(MATCH_PLANT_PROMPT, timeout=0.1)
                send_input(child, print_game, f'{plant_acres}\n')

            # Handle game end
            game_record = {}
            final_score = 0
            
            if not lost:
                print_calc('Waiting for game end\r\n')
                # try:
                child.expect(MATCH_FINAL_REPORT, timeout=0.1)
                pct_starved = float(child.match.group(1))
                try:
                    child.expect(MATCH_FINAL_REPORT_DEATHS, timeout=0.1)
                    total_deaths = int(child.match.group(1)) if child.match.group(1) else 0
                except (pexpect.TIMEOUT, pexpect.EOF):
                    child.expect(MATCH_FINAL_REPORT_NODEATHS, timeout=0.1)
                    total_deaths = 0

                game_record.update({
                    'pct_starved': pct_starved,
                    'total_deaths': total_deaths
                })
                final_score = determine_final_score(child)
                # except pexpect.TIMEOUT:
                #     print_calc('Timeout waiting for final report\r\n')
                    
            lost = lost or (final_score == 0)
            
            child.expect(pexpect.EOF, timeout=0.1)
                
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
            
            if lost:
                print_calc('We Lost :(\r\n')
                
        # except Exception as e:
        #     print_calc(f'Error: {e}\r\n')
        finally:
            child.close()

def determine_food_distribution(final_starting_bushels, population, final_acres, turn):
    # we can always starve 3% of our population without repercussion!
    starve_people = math.ceil(population * .03)

    for _ in range(starve_people, population - starve_people):
        grain_needed = calculate_grain_starved(population, starve_people, final_acres, turn)
        
        feed_people = (population - starve_people) * 20
        surplus = final_starting_bushels - grain_needed

        # starvation limit is 45%
        if starve_people > 0.45 * population:
            starve_people -= 1
            break

        if surplus > 0:
            break

        if final_starting_bushels - (feed_people // 2) < 0:
            break

        starve_people += 1
    
    feed_people = (population - starve_people) * 20
    plant_acres = 0 if turn == 10 else min(population * 10, final_acres, ((final_starting_bushels - feed_people) * 2) - 1)
    return plant_acres, feed_people

def calculate_grain_target(population, acres, turn):
    starve_people = math.ceil(population * .03)
    feed_population = (population - starve_people) * 20
    
    if turn == 10:
        return feed_population
        
    result = feed_population + (min(acres, population * 10) // 2) + 1
    return result

def calculate_grain_starved(population, starve_people, acres, turn):
    feed_population = (population - starve_people) * 20
    if turn == 10:
        return feed_population 
    result = feed_population + (min(acres, population * 10) // 2) + 1
    return result

def calc_land_sales(population, given_bushels, acres, acres_cost, turn):
    sell_acres = 0
    for sell_acres in range(0, acres + 1):
        grain_needed = calculate_grain_target(population, acres - sell_acres, turn)
        surplus = given_bushels + (sell_acres * acres_cost) - grain_needed 
        
        if surplus > 0:
            break
    return max(0, sell_acres)

def calc_land_purchases(population, given_bushels, acres, acres_cost, turn):
    MAX_BUY_ACRES = 999
    for buy_acres in range(0, MAX_BUY_ACRES + 2):
        grain_needed = calculate_grain_target(population, acres + buy_acres, turn)
        surplus = given_bushels - grain_needed - (buy_acres * acres_cost)

        if surplus < 0:
            buy_acres -= 1
            break
    return max(0, buy_acres)

def determine_final_score(child):
    # Try to match each possible ending
    patterns = [
        MATCH_NATIONAL_FINK,
        MATCH_UNPLEASANT, 
        MATCH_NOT_TOO_BAD,
        MATCH_FANTASTIC
        ]
    # return the index of the matching pattern
    # so MATCH_NATIONAL_FINK returns '0',
    # and 'MATCH_FANTASTIC'  is '3'
    return child.expect(patterns, timeout=0.2)

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
    main()
