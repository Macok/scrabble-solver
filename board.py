from dawg import *
import regex as re
import random
import copy


class Square:
    # default behavior is blank square, no score modifier, all cross-checks valid
    def __init__(self, letter=None, modifier="Normal", sentinel=1):
        self.letter = letter
        self.modifier = modifier
        self.visible = True
        if sentinel == 0:
            self.visible = False

    def __str__(self):
        if not self.visible:
            return ""
        if not self.letter:
            return "_"
        else:
            return self.letter


class ScrabbleBoard:
    def __init__(self, dawg_root):

        row_1 = \
            [Square(modifier="3WS"), Square(), Square(), Square(modifier="2LS"), Square(),
             Square(), Square(), Square(modifier="3WS"), Square(), Square(),
             Square(), Square(modifier="2LS"), Square(), Square(), Square(modifier="3WS"),
             Square(sentinel=0)]
        row_15 = copy.deepcopy(row_1)

        row_2 = \
            [Square(), Square(modifier="2WS"), Square(), Square(), Square(),
             Square(modifier="3LS"), Square(), Square(), Square(), Square(modifier="3LS"),
             Square(), Square(), Square(), Square(modifier="2WS"), Square(),
             Square(sentinel=0)]
        row_14 = copy.deepcopy(row_2)

        row_3 = \
            [Square(), Square(), Square(modifier="2WS"), Square(), Square(),
             Square(), Square(modifier="2LS"), Square(), Square(modifier="2LS"), Square(),
             Square(), Square(), Square(modifier="2WS"), Square(), Square(),
             Square(sentinel=0)]
        row_13 = copy.deepcopy(row_3)

        row_4 = \
            [Square(modifier="2LS"), Square(), Square(), Square(modifier="2WS"), Square(),
             Square(), Square(), Square(modifier="2LS"), Square(), Square(),
             Square(), Square(modifier="2WS"), Square(), Square(), Square(modifier="2LS"),
             Square(sentinel=0)]
        row_12 = copy.deepcopy(row_4)

        row_5 = \
            [Square(), Square(), Square(), Square(), Square(modifier="2WS"),
             Square(), Square(), Square(), Square(), Square(),
             Square(modifier="2WS"), Square(), Square(), Square(), Square(),
             Square(sentinel=0)]
        row_11 = copy.deepcopy(row_5)

        row_6 = \
            [Square(), Square(modifier="3LS"), Square(), Square(), Square(),
             Square(modifier="3LS"), Square(), Square(), Square(), Square(modifier="3LS"),
             Square(), Square(), Square(), Square(modifier="3LS"), Square(),
             Square(sentinel=0)]
        row_10 = copy.deepcopy(row_6)

        row_7 = \
            [Square(), Square(), Square(modifier="2LS"), Square(), Square(),
             Square(), Square(modifier="2LS"), Square(), Square(modifier="2LS"), Square(),
             Square(), Square(), Square(modifier="2LS"), Square(), Square(),
             Square(sentinel=0)]
        row_9 = copy.deepcopy(row_7)

        row_8 = \
            [Square(modifier="3WS"), Square(), Square(), Square(modifier="2LS"), Square(),
             Square(), Square(), Square(modifier="2WS"), Square(), Square(),
             Square(), Square(modifier="2LS"), Square(), Square(), Square(modifier="3WS"),
             Square(sentinel=0)]

        row_16 = [Square(sentinel=0) for _ in range(16)]

        # variables to describe board state
        self.board = [row_1, row_2, row_3, row_4, row_5, row_6, row_7, row_8,
                      row_9, row_10, row_11, row_12, row_13, row_14, row_15, row_16]

        self.point_dict = {"A": 1, "B": 3, "C": 3, "D": 2,
                           "E": 1, "F": 4, "G": 2, "H": 4,
                           "I": 1, "J": 8, "K": 5, "L": 1,
                           "M": 3, "N": 1, "O": 1, "P": 3,
                           "Q": 10, "R": 1, "S": 1, "T": 1,
                           "U": 1, "V": 4, "W": 4, "X": 8,
                           "Y": 8, "Z": 10, "%": 0}

        self.words_on_board = []

        self.is_transpose = False

        # variables to encode best word on a given turn
        self.dawg_root = dawg_root
        self.word_rack = []
        self.word_score_dict = {}
        self.best_word = ""
        self.highest_score = 0
        self.dist_from_anchor = 0
        self.letters_from_rack = []

        # rows and columns of highest-scoring word found so far.
        # these are the rows and columns of the tile already on the board
        self.best_row = 0
        self.best_col = 0


    # transpose method that modifies self.board inplace
    def _transpose(self):
        # https://datagy.io/python-transpose-list-of-lists/
        transposed_tuples = copy.deepcopy(list(zip(*self.board)))
        self.board = [list(sublist) for sublist in transposed_tuples]
        self.is_transpose = not self.is_transpose

    def vertical_check_letter(self, row, col, letter):
        word = letter
        r = row - 1
        while self.board[r][col].letter:
            word=self.board[r][col].letter+word
            r-=1
        r=row+1
        while self.board[r][col].letter:
            word=word+self.board[r][col].letter
            r+=1
        return len(word) == 1 or find_in_dawg(word, self.dawg_root)

    def vertical_check(self, row, col, word):
        if word=="IBEX" and row==8 and col==5:
            verbose=True
            print("CHECKING IBEX")
        else:
            verbose=False
        # make sure no letters before or after word
        if not self.board[row][col-1].modifier or not self.board[row][col+len(word)].modifier:
            return False

        for i in range(len(word)):
            if verbose:
                print("LETTER: "+word[i])
            if self.board[row][col+i].modifier:
                if verbose:
                    print("MODIFIER NOT EMPTY")
                if not self.vertical_check_letter(row, col+i, word[i]):
                    return False
        return True

    # TODO: fix scoring errors
    def _score_word(self, word, squares, dist_from_anchor):
        score = 0
        score_multiplier = 1

        if self.is_transpose:
            cross_sum_ind = "-"
        else:
            cross_sum_ind = "+"

        # word that will be inserted onto board shouldn't have wildcard indicator
        board_word = word.replace("%", "")

        coords = self.processing_row, self.processing_col - dist_from_anchor
        if not self.vertical_check(*coords, board_word):
            return

        # don't add words that are already on the board
        # TODO remove?
        if board_word in self.words_on_board:
            return board_word, 0

        # remove letters before wildcard indicators
        word = re.sub("[A-Z]%", "%", word)

        # maintain list of which tiles were pulled from word rack
        rack_tiles = []
        for letter, square in zip(word, squares):
            # add cross-sum by adding first and second letter scores from orthogonal two-letter word
            if cross_sum_ind in square.modifier:
                score += int(square.modifier[-1])
            if square.modifier:
                rack_tiles.append(letter)
            if "2LS" in square.modifier:
                score += (self.point_dict[letter] * 2)
            elif "3LS" in square.modifier:
                score += (self.point_dict[letter] * 3)
            elif "2WS" in square.modifier:
                score_multiplier *= 2
                score += self.point_dict[letter]
            elif "3WS" in square.modifier:
                score_multiplier *= 3
                score += self.point_dict[letter]
            else:
                score += self.point_dict[letter]

        if not rack_tiles:
            # no tiles used from rack
            return

        score *= score_multiplier

        # check for bingo
        if len(rack_tiles) == 7:
            score += 50

        if self.is_transpose:
            coords = coords[1], coords[0]
        self.all_moves.append((*coords, word, score, 'v' if self.is_transpose else 'h', rack_tiles))

        if score > self.highest_score:
            self.best_word = board_word
            self.highest_score = score
            # distance of leftmost placed tile from anchor. if anchor is leftmost tile distance will be 0.
            self.dist_from_anchor = dist_from_anchor
            self.letters_from_rack = rack_tiles

    def _extend_right(self, start_node, square_row, square_col, rack, word, squares, dist_from_anchor):
        square = self.board[square_row][square_col]

        # execute if square is empty
        if not square.letter:
            if start_node.is_terminal:
                self._score_word(word, squares, dist_from_anchor)
            for letter in start_node.children:
                # if square already has letters above and below it, don't try to extend
                if self.board[square_row + 1][square_col].letter and self.board[square_row - 1][square_col].letter:
                    continue

                # conditional for blank squares
                if letter in rack:
                    wildcard = False
                elif "%" in rack:
                    wildcard = True
                else:
                    continue
                if letter in rack and square.visible:
                    new_node = start_node.children[letter]
                    new_rack = rack.copy()
                    if wildcard:
                        new_word = word + letter + "%"
                        new_rack.remove("%")
                    else:
                        new_word = word + letter
                        new_rack.remove(letter)
                    new_squares = squares + [square]
                    self._extend_right(new_node, square_row, square_col + 1, new_rack, new_word, new_squares,
                                       dist_from_anchor)
        else:
            if square.letter in start_node.children:
                new_node = start_node.children[square.letter]
                new_word = word + square.letter
                new_squares = squares + [square]
                self._extend_right(new_node, square_row, square_col + 1, rack, new_word, new_squares,
                                   dist_from_anchor)

    def _left_part(self, start_node, anchor_square_row, anchor_square_col, rack, word, squares, limit,
                   dist_from_anchor):
        potential_square = self.board[anchor_square_row][anchor_square_col - dist_from_anchor]
        if potential_square.letter:
            return
        self._extend_right(start_node, anchor_square_row, anchor_square_col, rack, word, squares, dist_from_anchor)
        if not potential_square.visible:
            return
        if limit > 0:
            for letter in start_node.children:
                # conditional for blank squares
                if letter in rack:
                    wildcard = False
                elif "%" in rack:
                    wildcard = True
                else:
                    continue

                new_node = start_node.children[letter]
                new_rack = rack.copy()
                if wildcard:
                    new_word = word + letter + "%"
                    new_rack.remove("%")
                else:
                    new_word = word + letter
                    new_rack.remove(letter)
                new_squares = squares + [potential_square]
                self._left_part(new_node, anchor_square_row, anchor_square_col, new_rack, new_word, new_squares,
                                limit - 1, dist_from_anchor + 1)


    def print_board(self):
        print("    ", end="")
        [print(str(num).zfill(2), end=" ") for num in range(1, 16)]
        print()
        for i, row in enumerate(self.board):
            if i != 15:
                print(str(i + 1).zfill(2), end="  ")
            [print(square, end="  ") for square in row]
            print()
        print()

    # method to insert words into board by row and column number
    # using 1-based indexing for user input
    def insert_word(self, row, col, word):
        if len(word) + col > 15:
            print(f'Cannot insert word "{word}" at column {col + 1}, '
                  f'row {row + 1} not enough space')
            return
        curr_col = col
        modifiers = []
        for i, letter in enumerate(word):
            curr_square_letter = self.board[row][curr_col].letter
            modifiers.append(self.board[row][curr_col].modifier)
            # if current square already has a letter in it, check to see if it's the same letter as
            # the one we're trying to insert. If not, insertion fails, undo any previous insertions
            if curr_square_letter:
                if curr_square_letter == letter:
                    curr_col += 1
                else:
                    raise Exception(f"Failed to inserd word {word} at {row},{col}")
            else:
                self.board[row][curr_col].letter = letter

                # reset any modifiers to 0 once they have a tile placed on top of them
                self.board[row][curr_col].modifier = ""

                curr_col += 1

        self.words_on_board.append(word)

    # gets all words that can be made using a selected filled square and the current word rack
    def get_all_words(self, square_row, square_col, rack):
        # get all words that start with the filled letter
        self._extend_right(self.dawg_root, square_row, square_col, rack, "", [], 0)

        # create anchor square only if the space is empty
        if self.board[square_row][square_col - 1].letter:
            return

        # try every letter in rack as possible anchor square
        for i, letter in enumerate(rack):
            # Only allow anchor square with trivial cross-checks
            potential_square = self.board[square_row][square_col - 1]
            if not potential_square.visible or potential_square.letter:
                continue
            temp_rack = rack[:i] + rack[i + 1:]
            self.board[square_row][square_col - 1].letter = letter
            self._left_part(self.dawg_root, square_row, square_col - 1, temp_rack, "", [], 6, 1)

        # reset anchor square spot to blank after trying all combinations
        self.board[square_row][square_col - 1].letter = None

    # scan all tiles on board in both transposed and non-transposed state, find best move
    def get_best_move(self, word_rack):

        self.word_rack = word_rack

        # reset word variables to clear out words from previous turns
        self.best_word = ""
        self.highest_score = 0
        self.best_row = 0
        self.best_col = 0

        self.all_moves = []

        transposed = False
        for row in range(0, 15):
            for col in range(0, 15):
                curr_square = self.board[row][col]
                if curr_square.letter and (not self.board[row][col - 1].letter):
                    prev_best_score = self.highest_score
                    self.processing_row=row
                    self.processing_col=col
                    self.get_all_words(row, col, word_rack)
                    if self.highest_score > prev_best_score:
                        self.best_row = row
                        self.best_col = col

        self._transpose()
        for row in range(0, 15):
            for col in range(0, 15):
                curr_square = self.board[row][col]
                if curr_square.letter and (not self.board[row][col - 1].letter):
                    prev_best_score = self.highest_score
                    self.processing_row=row
                    self.processing_col=col
                    self.get_all_words(row, col, word_rack)
                    if self.highest_score > prev_best_score:
                        transposed = True
                        self.best_row = row
                        self.best_col = col

        self.all_moves = sorted(self.all_moves, key=lambda m:m[3], reverse=True)
        #print(self.all_moves)

        # Don't try to insert word if we couldn't find one
        if not self.best_word:
            self._transpose()
            return word_rack

        if transposed:
            self.insert_word(self.best_row, self.best_col - self.dist_from_anchor, self.best_word)
            self._transpose()
        else:
            self._transpose()
            self.insert_word(self.best_row, self.best_col - self.dist_from_anchor, self.best_word)

        self.word_score_dict[self.best_word] = self.highest_score

        for letter in self.letters_from_rack:
            if letter in word_rack:
                word_rack.remove(letter)

        return word_rack

    def get_start_move(self, word_rack):
        # board symmetrical at start so just always play the start move horizontally
        # try every letter in rack as possible anchor square
        self.best_row = 7
        self.best_col = 8
        self.all_moves = []
        for i, letter in enumerate(word_rack):
            potential_square = self.board[7][8]
            temp_rack = word_rack[:i] + word_rack[i + 1:]
            potential_square.letter = letter
            self.processing_row=7
            self.processing_col=8
            self._left_part(self.dawg_root, 7, 8, temp_rack, "", [], 6, 1)

        self.all_moves = sorted(self.all_moves, key=lambda m:m[3], reverse=True)

        # reset anchor square spot to blank after trying all combinations
        self.board[7][8].letter = None
        self.insert_word(self.best_row, self.best_col - self.dist_from_anchor, self.best_word)
        # self.board[7][8].modifier = "" that's a bug, modifier isn't changed here. Also should be reverted to "Standard", not ""
        self.word_score_dict[self.best_word] = self.highest_score

        for letter in self.letters_from_rack:
            if letter in word_rack:
                word_rack.remove(letter)

        return word_rack


# returns a list of all words played on the board
def all_board_words(board):
    board_words = []

    # check regular board
    for row in range(0, 15):
        temp_word = ""
        for col in range(0, 16):
            letter = board[row][col].letter
            if letter:
                temp_word += letter
            else:
                if len(temp_word) > 1:
                    board_words.append(temp_word)
                temp_word = ""

    # check transposed board
    for col in range(0, 16):
        temp_word = ""
        for row in range(0, 16):
            letter = board[row][col].letter
            if letter:
                temp_word += letter
            else:
                if len(temp_word) > 1:
                    board_words.append(temp_word)
                temp_word = ""

    return board_words


def refill_word_rack(rack, tile_bag):
    to_add = min([7 - len(rack), len(tile_bag)])
    new_letters = random.sample(tile_bag, to_add)
    rack = rack + new_letters
    return rack, new_letters


def play_game():
    #seed = random.randint(0, 10000)
    #random.seed(4005)
    score = 0
    tile_bag = ["A"] * 9 + ["B"] * 2 + ["C"] * 2 + ["D"] * 4 + ["E"] * 12 + ["F"] * 2 + ["G"] * 3 + \
               ["H"] * 2 + ["I"] * 9 + ["J"] * 1 + ["K"] * 1 + ["L"] * 4 + ["M"] * 2 + ["N"] * 6 + \
               ["O"] * 8 + ["P"] * 2 + ["Q"] * 1 + ["R"] * 6 + ["S"] * 4 + ["T"] * 6 + ["U"] * 4 + \
               ["V"] * 2 + ["W"] * 2 + ["X"] * 1 + ["Y"] * 2 + ["Z"] * 1 + ["%"] * 2

    to_load = open("lexicon/scrabble_words_complete.pickle", "rb")
    root = pickle.load(to_load)
    to_load.close()
    word_rack = random.sample(tile_bag, 7)
    [tile_bag.remove(letter) for letter in word_rack]
    game = ScrabbleBoard(root)
    word_rack = game.get_start_move(word_rack)
    score += game.highest_score
    word_rack, new_letters = refill_word_rack(word_rack, tile_bag)
    [tile_bag.remove(letter) for letter in new_letters]

    play = True
    while play:
        # game.print_board()
        for word in all_board_words(game.board):
            if not find_in_dawg(word, root) and word:
                raise Exception(f"Invalid word on board: {word}")
        word_rack = game.get_best_move(word_rack)
        score += game.highest_score
        word_rack, new_letters = refill_word_rack(word_rack, tile_bag)
        [tile_bag.remove(letter) for letter in new_letters]
        if game.best_word == "":
            # draw new hand if can't find any words
            if len(tile_bag) >= 7:
                return_to_bag_words = word_rack.copy()
                word_rack, new_letters = refill_word_rack([], tile_bag)
                [tile_bag.remove(letter) for letter in new_letters]

            else:
                play = False
                for word in all_board_words(game.board):
                    if not find_in_dawg(word, root) and word:
                        game.print_board()
                        #print(seed)
                        raise Exception(f"Invalid word on board: {word}")

    game.print_board()

    return score


state = """
   some        |
    t          |
    h          |
    elastic    |
    r    n     |
         t     |
         e     |
         r     |
         n     |
         a     |
         l     |
               |
               |
               |
               |
"""


if __name__ == "__main__":
    while True:
        score = play_game()
        print(f"score: {score}")


if __name__ == "__main__123":
    scores = []
    runs = 150
    for _ in range(runs):
        scores.append(play_game())

    print(sum(scores) / runs)


if __name__ == "__main__123":
    to_load = open("lexicon/scrabble_words_complete.pickle", "rb")
    with open("lexicon/scrabble_words_complete.pickle", "rb") as f:
        root = pickle.load(f)
    game = ScrabbleBoard(root)
    game.get_start_move(["Q", "X", "R"])
    if not game.all_moves:
        print("No move found")
    for move in game.all_moves[:15]:
        print(move)
    game.print_board()


if __name__ == "__main__123":
    to_load = open("lexicon/scrabble_words_complete.pickle", "rb")
    with open("lexicon/scrabble_words_complete.pickle", "rb") as f:
        root = pickle.load(f)
    game = ScrabbleBoard(root)

    row=0
    col=0
    i=0
    while i<len(state):
        char = state[i]
        if char==' ':
            col+=1
        elif 'a' <= char <= 'z':
            game.board[row][col].letter=char.upper()
            game.board[row][col].modifier=""
            col+=1
        elif char == '|':
            col=0
            row+=1
        i+=1

    game.get_best_move(["X"])
    if not game.all_moves:
        print("No move found")
    for move in game.all_moves[:15]:
        print(move)

    game.print_board()