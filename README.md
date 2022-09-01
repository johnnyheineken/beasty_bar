# Beasty bar (Python implementation)

If you don't know the game, have a look at the info
at [Board Game Geek](https://boardgamegeek.com/boardgame/165950/beasty-bar). Simple card game. 5 card in the queue,
several cards in the hand. Players take turn to put the given card on the table. Each of the card have unique action.
Who gets most of the cards into the _beasty bar_ wins.

I really like the game and I decided that it would be fun to look at the game.

- How hard it is to implement the game? (Surprisingly hard, i.e. the queue management was first to me.)
- What will be the optimal strategy? (I don't know yet.)

## Run:
In order to get a single played game for 4 players, run 
```
python safari.py
```
You should get a log of the single game.  
Works with Python 3.10.

## Tests:

The logic in the queue is quite complicated and in order to implement that, I tried _test driven development_.
In order to see how the tests work, see pytest.

## What is the optimal strategy?

I don't know yet!  
My current plan of action is following.
- create more intuitive interface for players (see players/strategies.py).
This interface needs to set several things:
  - which card to choose from hand
  - what action chameleon should play
  - what action parrot should play.  
    
I will create several thousand games and have a look.
Then I would like to see:
- the most successful card at each turn
- Analyse the most successful strategies
- Analyse the most successful games