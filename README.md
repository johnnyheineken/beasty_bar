# Beasty bar (Python implementation)

If you don't know the game, have a look at the info
at [Board Game Geek](https://boardgamegeek.com/boardgame/165950/beasty-bar). Simple card game. 5 card in the queue,
several cards in the hand. Players take turn to put the given card on the table. Each of the card have unique action.
Who gets most of the cards into the _beasty bar_ wins.

I really like the game and I decided that it would be fun to look at the game.

- How hard it is to implement the game? (Surprisingly hard, i.e. the queue management was first to me.)
- What will be the optimal strategy? (I don't know yet.)

## Play in the browser (multiplayer)

```
python webapp/server.py
```

Then open http://localhost:8000. Create a game, pick a deck and the number
of human players, and share the invite link with friends — empty seats are
filled with AI. The UI is optimized for phones.

Decks:

- 🦁 **Classic** — the original 12 animals; most guests in the bar wins
  (ties broken by the lower total card value).
- 🦏 **New Beasts in Town** — the 12 expansion animals (rhino, bear, tiger,
  cheetah, llama, porcupine, ostrich, penguin, dog, peacock, vulture, bat);
  the card points decide the winner.
- 🔀 **Mixed** — every player gets a random pick of one animal per value
  (1–12) from the two sets, points scoring. (The official combined rules
  let each player draft their own 12; the random pick keeps the UI simple.)

All in-game decisions are interactive: parrot/bat targets, kangaroo jump
length, ostrich parity, chameleon species, penguin hand-card imitation, and
the choices of a card revived by the vulture. Rare tie-breaking choices
(rhino/cheetah/peacock with several equally strong targets) currently use
a sensible default instead of a prompt.

The server uses only the Python standard library — no dependencies needed.
A `Dockerfile`/`Procfile` are included if you want to host it somewhere
permanent (Render, Fly.io, Railway, …).

## Run a simulated game:
In order to get a single played game for 4 AI players, run
```
python logic.py
```
You should get a log of the single game.  
Works with Python 3.10+.

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