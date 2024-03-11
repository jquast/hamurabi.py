Hamurabi.py
===========

A modern python port of the BASIC game, `Hamurabi
<https://en.wikipedia.org/wiki/Hamurabi_(video_game)>`_

A very special thanks to the first author of the first Strategy game, `David A.
Ahl <https://en.wikipedia.org/wiki/David_H._Ahl>`_, who authored the book, BASIC
Computer Games, which inspired so many people to write and share their own, and
most especially, the spirit of sharing the source code, and to encourage
education through the study and play of computer games in general.

From `page 78 <https://www.atariarchives.org/basicgames/showpage.php?page=78>`_
of `BASIC Computer games <https://en.wikipedia.org/wiki/BASIC_Computer_Games>`_:

  In this game you direct the administrator of Sumeria, Hammurabi, how to
  manage the city. The city initially has 1,000 acres, 100 people, and 3,000
  bushels of grain in storage.

  You may buy and sell land with your neighboring city-states for bushels of
  grain -- the price will vary between 17 and 26 bushels per acre. You also
  must use grain to feed your people and as seed to plant the next year's
  crop.

  You will quickly find that a certain number of people can only tend a certain
  amount of land and that people starve if they are not fed enough. You also
  have the unexpected to contend with such as a plague, rats destroying stored
  grain, and variable harvests.

  You will also find that managing just the few resources in this game is not a
  trivial job over a period of say ten years. The crisis of population density
  rears its head very rapidly.

play-hamurabi-vs-apple-1.py
===========================

This is an "autoplayer", it loads the Apple 1 port of HAMURABI.BAS using wozmon
bytes and plays an optimized game against it, winning 99.5% of games played, 94%
of games are won at the highest level by systematically starving 3% of the
population. More details published at https://www.jeffquast.com/post/hamurabi_bas/
