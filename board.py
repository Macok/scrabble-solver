from dawg import build_dawg, find_in_dawg
import copy
import time


class Square:
    # default behavior is blank square, no score modifier, all cross-checks valid
    def __init__(self, letter=None, modifier=None, sentinel=1):
        self.letter = letter
        self.cross_checks = [sentinel] * 26
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
             Square(), Square(), Square(modifier="START"), Square(), Square(),
             Square(), Square(modifier="2LS"), Square(), Square(), Square(modifier="3WS"),
             Square(sentinel=0)]

        row_16 = [Square(sentinel=0) for _ in range(16)]

        self.board = [row_1, row_2, row_3, row_4, row_5, row_6, row_7, row_8,
                      row_9, row_10, row_11, row_12, row_13, row_14, row_15, row_16]

        self.dawg_root = dawg_root

        self.words_on_board = []

        # variables to encode best word on a given turn
        self.word_score_dict = {}
        self.best_word = ""
        self.highest_score = 0
        self.dist_from_anchor = 0
        # rows and columns of highest-scoring word found so far.
        # these are the rows and columns of the tile already on the board
        self.best_row = 0
        self.best_col = 0

        # store squares that need updated cross-checks
        self.upper_cross_check = []
        self.lower_cross_check = []

    # transpose method that modifies self.board inplace
    def _transpose(self):
        # https://datagy.io/python-transpose-list-of-lists/
        transposed_tuples = copy.deepcopy(list(zip(*self.board)))
        self.board = [list(sublist) for sublist in transposed_tuples]

    # TODO: implement score multipliers
    def _score_word(self, word, dist_from_anchor):
        # don't add words that are already on the board
        if word in self.words_on_board:
            return word, 0

        score = 0
        point_dict = {"A": 1, "B": 3, "C": 3, "D": 2,
                      "E": 1, "F": 4, "G": 2, "H": 4,
                      "I": 1, "J": 8, "K": 5, "L": 1,
                      "M": 3, "N": 1, "O": 1, "P": 3,
                      "Q": 10, "R": 1, "S": 1, "T": 1,
                      "U": 1, "V": 4, "W": 4, "X": 8,
                      "Y": 8, "Z": 10}

        for letter in word:
            score += point_dict[letter]

        if score > self.highest_score:
            self.best_word = word
            self.highest_score = score
            # distance of leftmost placed tile from anchor. if anchor is leftmost tile distance will be 0.
            self.dist_from_anchor = dist_from_anchor

        return word, score

    def _extend_right(self, start_node, square_row, square_col, rack, word, dist_from_anchor):
        square = self.board[square_row][square_col]

        # execute if square is empty
        if not square.letter:
            if start_node.is_terminal:
                word, score = self._score_word(word, dist_from_anchor)
                self.word_score_dict[word] = score
            for letter in rack:
                if letter in start_node.children and self._cross_check(letter, square.cross_checks):
                    new_node = start_node.children[letter]
                    new_rack = rack.copy()
                    new_rack.remove(letter)
                    new_word = word + letter
                    self._extend_right(new_node, square_row, square_col + 1, new_rack, new_word, dist_from_anchor)
        else:
            if square.letter in start_node.children:
                new_node = start_node.children[square.letter]
                new_word = word + square.letter
                self._extend_right(new_node, square_row, square_col + 1, rack, new_word, dist_from_anchor)

    def _left_part(self, start_node, anchor_square_row, anchor_square_col, rack, word, limit, dist_from_anchor):
        # don't love this, but this seems to be unstated part of paper's implementation. Only allow
        # left parts where cross-checks are nontrivial
        potential_square = self.board[anchor_square_row][anchor_square_col - dist_from_anchor + 1]
        if not all(potential_square.cross_checks):
            return
        self._extend_right(start_node, anchor_square_row, anchor_square_col, rack, word, dist_from_anchor)
        if limit > 0:
            for letter in rack:
                if letter in start_node.children:
                    new_node = start_node.children[letter]
                    new_rack = rack.copy()
                    new_rack.remove(letter)
                    new_word = word + letter
                    self._left_part(new_node, anchor_square_row, anchor_square_col, new_rack, new_word, limit - 1,
                                    dist_from_anchor + 1)

    def _update_cross_checks(self):
        while self.upper_cross_check:
            curr_square, lower_letter, lower_row, lower_col = self.upper_cross_check.pop()
            chr_val = 65
            for i, ind in enumerate(curr_square.cross_checks):
                if ind == 1:
                    test_node = self.dawg_root.children[chr(chr_val)]
                    if (lower_letter not in test_node.children) or (not test_node.children[lower_letter].is_terminal):
                        curr_square.cross_checks[i] = 0
                chr_val += 1

        while self.lower_cross_check:
            curr_square, upper_letter, upper_row, upper_col = self.lower_cross_check.pop()
            chr_val = 65
            for i, ind in enumerate(curr_square.cross_checks):
                if ind == 1:
                    test_node = self.dawg_root.children[upper_letter]
                    if (chr(chr_val) not in test_node.children) or (not test_node.children[chr(chr_val)].is_terminal):
                        curr_square.cross_checks[i] = 0
                chr_val += 1

    def _cross_check(self, letter, cross_checks):
        chr_val = 65
        for i, ind in enumerate(cross_checks):
            if ind == 1:
                if chr(chr_val) == letter:
                    return True
            chr_val += 1
        return False

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
        row -= 1
        col -= 1
        print(row, col, word)
        if len(word) + col > 15:
            print(f'Cannot insert word "{word}" at column {col + 1}, '
                  f'row {row + 1} not enough space')
            return
        curr_col = col
        for i, letter in enumerate(word):
            curr_square_letter = self.board[row][curr_col].letter
            # if current square already has a letter in it, check to see if it's the same letter as
            # the one we're trying to insert. If not, insertion fails, undo any previous insertions
            if curr_square_letter:
                if curr_square_letter == letter:
                    if row > 0:
                        self.upper_cross_check.append((self.board[row - 1][curr_col], letter, row, curr_col))
                    if row < 15:
                        self.lower_cross_check.append((self.board[row + 1][curr_col], letter, row, curr_col))

                    curr_col += 1
                else:
                    print(f'Failed to insert letter "{letter}" of "{word}" at column {curr_col + 1}, '
                          f'row {row + 1}. Square is occupied by letter "{curr_square_letter}"')
                    self.upper_cross_check = []
                    self.lower_cross_check = []
                    for _ in range(i):
                        curr_col -= 1
                        self.board[row][curr_col].letter = None
                    return
            else:
                # once letter is inserted, add squares above and below it to cross_check_queue
                if row > -1:
                    self.upper_cross_check.append((self.board[row - 1][curr_col], letter, row, curr_col))
                if row < 15:
                    self.lower_cross_check.append((self.board[row + 1][curr_col], letter, row, curr_col))

                self.board[row][curr_col].letter = letter
                curr_col += 1

        # place 0 cross-check sentinel at the beginning and end of inserted words to stop accidental overlap
        if curr_col < 15:
            self.board[self.best_row][curr_col].cross_checks = [0] * 26
        if col - 1 > - 1:
            self.board[self.best_row][col - 1].cross_checks = [0] * 26

        self.words_on_board.append(word)

        # TODO: makes shit weird
        print(self.upper_cross_check)
        print(self.lower_cross_check)
        # self._update_cross_checks()

    # gets all words that can be made using a selected filled square and the current word rack
    def get_all_words(self, square_row, square_col, rack, word=""):
        square_row -= 1
        square_col -= 1

        # get all words that start with the filled letter
        self._extend_right(self.dawg_root, square_row, square_col, rack, word, 0)

        # prevent generation of words with left parts that wouldn't fit on the board
        limit = 6
        if square_col < 7:
            limit = square_col - 1

        # create anchor square only if the space is empty
        if self.board[square_row][square_col - 1].letter:
            return

        # try every letter in rack as possible anchor square
        for i, letter in enumerate(rack):
            temp_rack = rack[:i] + rack[i + 1:]
            self.board[square_row][square_col - 1].letter = letter
            self._left_part(self.dawg_root, square_row, square_col - 1, temp_rack, "", limit, 1)

        # reset anchor square spot to blank after trying all combinations
        self.board[square_row][square_col - 1].letter = None

    # scan all tiles on board in both transposed and non-transposed state, find best move
    def get_best_move(self, word_rack):

        # clear out cross-check lists before adding new words
        self._update_cross_checks()

        # reset word variables to clear out words from previous turns
        self.word_score_dict = {}
        self.best_word = ""
        self.highest_score = 0
        self.best_row = 0
        self.best_col = 0

        transposed = False
        for row in range(0, 15):
            for col in range(0, 15):
                curr_square = self.board[row][col]
                if curr_square.letter and (not self.board[row][col - 1].letter):
                    prev_best_word = self.best_word
                    self.get_all_words(row + 1, col + 1, word_rack)
                    if self.best_word != prev_best_word:
                        self.best_row = row
                        self.best_col = col

        self._transpose()

        for row in range(0, 15):
            for col in range(0, 15):
                curr_square = self.board[row][col]
                if curr_square.letter and (not self.board[row][col - 1].letter):
                    prev_best_word = self.best_word
                    self.get_all_words(row + 1, col + 1, word_rack)
                    if self.best_word != prev_best_word:
                        transposed = True
                        self.best_row = row
                        self.best_col = col

        if transposed:
            self.insert_word(self.best_row + 1, self.best_col + 1 - self.dist_from_anchor, self.best_word)
            self._transpose()

        else:
            self._transpose()
            self.insert_word(self.best_row + 1, self.best_col + 1 - self.dist_from_anchor, self.best_word)


big_list = open("lexicon/scrabble_words_complete.txt", "r").readlines()
big_list = [word.strip("\n") for word in big_list]
root = build_dawg(big_list)

word_rack = ["E", "O", "U", "C", "T", "R", "A"]
scrabble_board = ScrabbleBoard(root)
scrabble_board.insert_word(1, 7, "SIT")
scrabble_board.print_board()
for _ in range(50):
    scrabble_board.get_best_move(word_rack)
    print(scrabble_board.words_on_board)
    scrabble_board.print_board()

print(scrabble_board.board[3][7].cross_checks)