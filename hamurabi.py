"""
Hamurabi.py -- a modern python port of the BASIC game, Hamurabi!
"""
import sys
import random
import textwrap

# 10 REM *** CONVERTED FROM THE ORIGINAL FOCAL PROGRAM AND MODIFIED
# 20 REM *** FOR EDUSYSTEM 70 BY DAVID AHL, DIGITAL
# 30 REM *** MODIFIED FOR 8K MICROSOFT BASIC BY PETER TURNBULL
# Converted to python 3 by Jeff Quast.
#
# 90 REM RANDOMIZE REMOVED
def main():
    # 80 PRINT "TRY YOUR HAND AT GOVERNING ANCIENT SUMERIA"
    # 85 PRINT "SUCCESSFULLY FOR A 10-YR TERM OF OFFICE.":PRINT
    # 95 D1=0:P1=0
    total_dead = 0
    pct_starve = 0

    # 110 Z=0:P=95:S=2800:H=3000:E=H-S
    population = 95  # population
    bushels = 2800  # bushels in storage
    harvested = 3000  #
    eaten = harvested - bushels  # bushels eaten by rats

    # 120 Y=3:A=H/Y:I=5:Q=1
    harv_yield = 3  # initial Harvested per acre
    acres = harvested // harv_yield  # How many acres do we have?
    infants = 5  # How many infants
    plague_chance = 1

    # 210 D=0
    dead = 0

    for year in range(1, 11):
        # 215 PRINT:PRINT:PRINT "HAMURABI:  I BEG TO REPORT TO YOU,":Z=Z+1
        # 217 PRINT "IN YEAR"Z","D"PEOPLE STARVED,"I"CAME TO THE CITY."
        echo()
        echo(f"Hamurabi: I beg to report to you,")
        echo(f"In year {year}, {dead} people starved, "
             f"{infants} came to the city.")

        # 218 P=P+I
        population = population + infants

        # 227 IF Q>0 THEN 230
        if plague_chance <= 0:
            # 228 P=INT(P/2)
            # 229 PRINT "A HORRIBLE PLAGUE STRUCK!  HALF THE PEOPLE DIED."
            population = population // 2
            echo("A horrible plague struck!! Half the people have perished.")

        # 230 PRINT "POPULATION IS NOW"P
        # 232 PRINT "THE CITY NOW OWNS"A"ACRES."
        # 235 PRINT "YOU HARVESTED"Y"BUSHELS PER ACRE."
        # 250 PRINT "RATS ATE"E"BUSHELS."
        # 260 PRINT "YOU NOW HAVE"S"BUSHELS IN STORE.":PRINT
        echo(f"Population is now {population}")
        echo(f"The city now owns {acres} acres.")
        echo(f"You harvested {harv_yield} bushels per acre.")
        if eaten:
            echo(f"Rats have eaten {eaten} bushels from storage!")
        echo(f"You now have {bushels} bushels.\n")

        # 270 IF Z=11 THEN 860
        if year == 10:
            break

        # 310 C=INT(10*RND(1)):Y=C+17
        land_value = int(10 * random.random()) + 17

        # 312 PRINT "LAND IS TRADING AT"Y"BUSHELS PER ACRE."
        echo(f"Land is trading at {land_value} bushels per acre.")
        echo()

        # 320 PRINT "HOW MANY ACRES DO YOU WISH TO BUY";
        buy_land = buy_acres_320(land_value, bushels)

        # 330 IF Q=0 THEN 340
        if buy_land == 0:
            # 340 PRINT "HOW MANY ACRES DO YOU WISH TO SELL";
            sell_land = sell_acres_340(acres)
            if sell_land > 0:
                # 350 A=A-Q:S=S+Y*Q:C=0
                acres = acres - sell_land
                bushels += land_value * sell_land
        else:
            # 331 A=A+Q:S=S-Y*Q:C=0
            acres = acres + buy_land
            bushels -= land_value * buy_land

        # 410 PRINT "HOW MANY BUSHELS DO YOU WISH TO FEED YOUR PEOPLE";
        # 430 S=S-Q:C=1:PRINT
        people_food = feed_people_400(bushels)
        bushels -= people_food

        # 440 PRINT "HOW MANY ACRES DO YOU WISH TO PLANT WITH SEED";
        # 510 S=S-INT(D/2)
        planted = plant_seeds_440(acres, population, bushels)
        bushels -= (planted // 2)

        # 511 GOSUB 800
        # 512 REM *** A BOUNTIFUL HARVEST!!
        # 515 Y=C:H=D*Y:E=0
        harv_yield = rand_gosub_800()
        harvested = planted * harv_yield

        # 521 GOSUB 800
        # 522 IF INT(C/2)<>C/2 THEN 530
        # 523 REM *** THE RATS ARE RUNNING WILD!!
        # 525 E=INT(S/C)
        eaten = 0
        rat_chance = rand_gosub_800()
        if rat_chance % 2 == 0:
            eaten = bushels // rat_chance
        # 530 S=S-E+H
        bushels = bushels - eaten + harvested

        # 531 GOSUB 800
        # 532 REM *** LET'S HAVE SOME BABIES
        # 533 I=INT(C*(20*A+S)/P/100+1)
        _randc = rand_gosub_800()
        infants = int(_randc * (20 * acres + bushels) / population / 100 + 1)

        # 539 REM *** HOW MANY PEOPLE HAD FULL TUMMIES?
        # 540 C=INT(Q/20)
        full_tummies = people_food // 20

        # 541 REM *** HORRORS, A 15% CHANCE OF PLAGUE
        # 542 Q=INT(10*(2*RND(1)-.3))

        plague_chance = int(10 * (2 * random.random() - .3))

        # 550 IF P<C THEN 210
        if population < full_tummies:
            continue

        # 551 REM *** STARVE ENOUGH FOR IMPEACHMENT?
        # 552 D=P-C:IF D>.45*P THEN 560
        # 553 P1=((Z-1)*P1+D*100/P)/Z
        # 555 P=C:D1=D1+D:GOTO 215
        dead = population - full_tummies
        if dead > .45 * population:
            # 560 PRINT:PRINT "YOU STARVED"D"PEOPLE IN ONE YEAR!!!"
            echo()
            echo(f"You starved {dead} people in one year!!!")
            declare_national_fink_565()
        pct_starve = ((year - 1) * pct_starve + dead * 100 / population) / year
        population = full_tummies
        total_dead += dead

    # 860 PRINT "IN YOUR 10-YEAR TERM OF OFFICE,"P1"PERCENT OF THE"
    # 862 PRINT "POPULATION STARVED PER YEAR ON AVERAGE, I.E., A TOTAL OF"
    # 865 PRINT D1"PEOPLE DIED!!":L=A/P
    maybe_died = "and nobody died of starvation!!"
    if total_dead:
        maybe_died = f"{total_dead} people DIED of starvation!!"
    echo(f"In your 10-year term of office, {pct_starve:2.2f}% of the "
         f"population starved, in other words, {maybe_died}")
    wealth = acres / population
    # 870 PRINT "YOU STARTED WITH 10 ACRES PER PERSON AND ENDED WITH"
    # 875 PRINT L"ACRES PER PERSON.":PRINT
    echo("You started with 10 acres per person, and ended with {wealth:2.2f}.")

    # 880 IF P1>33 THEN 565
    # 885 IF L<7 THEN 565
    if pct_starve > 33 or wealth < 7:
        declare_national_fink_565()
    # 890 IF P1>10 THEN 940
    # 892 IF L<9 THEN 940
    elif pct_starve > 10 or wealth < 9:
        # 940 PRINT "YOUR HEAVY-HANDED PERFORMANCE SMACKS OF NERO AND IVAN IV."
        # 945 PRINT "THE PEOPLE (REMAINING) FIND YOU AN UNPLEASANT RULER, AND,"
        # 950 PRINT "FRANKLY, HATE YOUR GUTS!":GOTO 990
        echo("Your heavy-handed performance smacks of Nero and Ivan IV. "
             "The people (remaining) find you an unpleasant ruler, and, "
             "frankly, hate your guts!")
    elif pct_starve > 3 or wealth < 10:
        # 960 PRINT "YOUR PERFORMANCE COULD HAVE BEEN SOMEWHAT BETTER, BUT"
        # 965 PRINT "REALLY WASN'T TOO BAD AT ALL. ";
        # 966 PRINT INT(P*.8*RND(1));"PEOPLE WOULD"
        # 970 PRINT "DEARLY LIKE TO SEE YOU ASSASSINATED BUT WE ALL HAVE OUR"
        # 975 PRINT "TRIVIAL PROBLEMS."
        echo("Your performance could have been somewhat better, "
             "but really wasn't too bad at all. "
             "{int(population * .8 * random.random())} people "
             "would dearly like to see you assassinated, but we "
             "all have our trivial problems.")
    else:
        # 900 PRINT "A FANTASTIC PERFORMANCE!!!  CHARLEMANGE, DISRAELI, AND"
        # 905 PRINT "JEFFERSON COMBINED COULD NOT HAVE DONE BETTER!":GOTO 990
        echo("A fantastic performance!!! Charlemange, Disraeli, and "
             "Jefferson combined could not have done better!")
    beeping_end_990()


def buy_acres_320(land_value, bushels):
    # 321 INPUT Q:IF Q<0 THEN 850
    # 322 IF Y*Q<=S THEN 330
    # 323 GOSUB 710
    while True:
        num = input_numeric("How many acres do you wish to buy (0 to sell)? ")
        if num < 0:
            steward_quits_850()
        if land_value * num <= bushels:
            return num
        not_enough_bushels_710(bushels)


def sell_acres_340(acres):
    # 341 INPUT Q:IF Q<0 THEN 850
    # 342 IF Q<A THEN 350
    # 344 GOTO 340
    while True:
        num = input_numeric("How many acres do you wish to sell? ")
        if num < 0:
            steward_quits_850()
        if num < acres:
            return num
        think_again_only_acres_720(acres)


def feed_people_400(bushels):
    # 411 INPUT Q
    # 412 IF Q<0 THEN 850
    # 418 REM *** TRYING TO USE MORE GRAIN THAN IN THE SILOS?
    # 420 IF Q<=S THEN 430
    # 421 GOSUB 710
    # 422 GOTO 410
    while True:
        num = input_numeric("How many bushels do you wish "
                            "to feed your people? ")
        if num < 0:
            steward_quits_850()
        if num <= bushels:
            return num
        not_enough_bushels_710(bushels)


def plant_seeds_440(acres, population, bushels):
    # 440 PRINT "HOW MANY ACRES DO YOU WISH TO PLANT WITH SEED";
    # 441 INPUT D:IF D=0 THEN 511
    # 442 IF D<0 THEN 850
    # 444 REM *** TRYING TO PLANT MORE ACRES THAN YOU OWN?
    # 445 IF D<=A THEN 450
    # 446 GOSUB 720
    # 447 GOTO 440
    # 449 REM *** ENOUGH GRAIN FOR SEED?
    # 450 IF INT(D/2)<S THEN 455
    # 452 GOSUB 710
    # 453 GOTO 440
    # 454 REM *** ENOUGH PEOPLE TO TEND THE CROPS?
    # 455 IF D<10*P THEN 510
    # 460 PRINT "BUT YOU HAVE ONLY"P"PEOPLE TO TEND THE FIELDS. NOW THEN,"
    # 470 GOTO 440
    while True:
        num = input_numeric("How many acres do you wish to plant with seed? ")
        if num < 0:
            steward_quits_850()
        if num <= acres:
            planted = bushels - (num // 2)
            if planted < 0:
                not_enough_bushels_710(bushels)
                continue
            if num <= 10 * population:
                return num
            echo(f"But you only have {population} people "
                 "to tend the fields. Now then,")
        else:
            think_again_only_acres_720(acres)


def declare_national_fink_565():
    # 565 PRINT "DUE TO THIS EXTREME MISMANAGEMENT YOU HAVE NOT ONLY"
    # 566 PRINT "BEEN IMPEACHED AND THROWN OUT OF OFFICE BUT YOU HAVE"
    # 567 PRINT "ALSO BEEN DECLARED 'NATIONAL FINK' !!":GOTO 990
    echo()
    echo("Due to this extreme mismanagement, you have not only been "
         "impeached and thrown out of office, but you have also been "
         "declared 'NATIONAL FINK' !!")
    beeping_end_990()


def not_enough_bushels_710(bushels):
    # 710 PRINT "HAMURABI:  THINK AGAIN. YOU HAVE ONLY"
    # 711 PRINT S"BUSHELS OF GRAIN.  NOW THEN,"
    # 712 RETURN
    echo(f"Hamurabi: Think again. You have only {bushels} "
         "bushels of grain. Now then,")


def think_again_only_acres_720(acres):
    # 720 PRINT "HAMURABI:  THINK AGAIN. YOU OWN ONLY"A"ACRES.  NOW THEN,"
    # 730 RETURN
    echo(f'Hamurabi: Think again. You only have {acres} Acres. Now then,')


def rand_gosub_800():
    # 800 C=INT(RND(1)*5)+1
    # 801 RETURN
    return int(random.random() * 5) + 1


def input_numeric(message, default=0):
    while True:
        val = input(message)
        try:
            return int(val)
        except ValueError as err:
            if val.strip():
                echo(f"Not a number, {val!r}: {err}")
                continue
            return default


def beeping_end_990():
    # 990 PRINT:FOR N=1 TO 10:PRINT CHR$(7);:NEXT N
    # 995 PRINT "SO LONG FOR NOW.":PRINT
    # 999 END
    echo()
    echo(('\b' * 10) + "So long for now.")
    sys.exit()


def steward_quits_850():
    # 850 PRINT:PRINT "HAMURABI:  I CANNOT DO WHAT YOU WISH."
    # 855 PRINT "GET YOURSELF ANOTHER STEWARD!!!!!"
    # 857 GOTO 990
    print('\nHamurabi: I cannot do what you wish.')
    print('Get yourself another steward!!!!!')
    beeping_end_990()

def echo(text='', **kwargs):
    print('\n'.join(textwrap.wrap(text, 70, **kwargs)))


if __name__ == '__main__':
    main()
