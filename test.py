import keyboard
import mouse
import pyautogui
from colormath.color_objects import sRGBColor, LabColor
from colormath.color_conversions import convert_color
from colormath.color_diff import delta_e_cie2000
import time
import numpy as np
from TetrisBoard import TetrisBoard


# Each piece is represented by a 2D array, and rotations are stored as a list of 2D arrays
# 4x4 pieces are padded with 0s to make them 4x4
tetris_pieces = {
    'I': [
        np.array([[1, 1, 1, 1]]),
        np.array([[0, 1, 0, 0], [0, 1, 0, 0], [0, 1, 0, 0], [0, 1, 0, 0]])
    ],
    'O': [
        np.array([[0, 1, 1, 0], [0, 1, 1, 0]])
    ],
    'T': [
        np.array([[1, 1, 1, 0], [0, 1, 0, 0]]),
        np.array([[0, 1, 0, 0], [0, 1, 1, 0], [0, 1, 0, 0]]),
        np.array([[0, 1, 0, 0], [1, 1, 1, 0]]),
        np.array([[0, 1, 0, 0], [1, 1, 0, 0], [0, 1, 0, 0]]),
    ],
    'L': [
        np.array([[1, 1, 1, 0], [0, 0, 1, 0]]),
        np.array([[0, 1, 1, 0], [0, 1, 0, 0], [0, 1, 0, 0]]),
        np.array([[1, 0, 0, 0], [1, 1, 1, 0]]),
        np.array([[0, 1, 0, 0], [0, 1, 0, 0], [0, 1, 0, 0], [0, 1, 1, 0]]),
    ],
    'L2': [
        np.array([[1, 1, 1, 0], [1, 0, 0, 0]]),
        np.array([[0, 1, 0, 0], [0, 1, 0, 0], [0, 1, 1, 0]]),
        np.array([[0, 0, 1, 0], [1, 1, 1, 0]]),
        np.array([[0, 1, 0, 0], [0, 1, 0, 0], [0, 1, 1, 0]]),
    ],
    'Z': [
        np.array([[0, 1, 1, 0], [1, 1, 0, 0]]),
        np.array([[0, 1, 0, 0], [0, 1, 1, 0], [0, 0, 1, 0]])
    ],
    'Z2': [
        np.array([[1, 1, 0, 0], [0, 1, 1, 0]]),
        np.array([[0, 0, 1, 0], [0, 1, 1, 0], [0, 1, 0, 0]])
    ]
}


def evaluate_board(board):
    # Implement your heuristic function here
    # The height of the tallest column - find highest row with a 1
    highest_block_row = 20
    for row in range(board.shape[0]):
        if not np.any(board[row] == 1):
            highest_block_row = row
            break
    # The sum of max height block in each column - the bottom of the board is index 0
    sum_of_heights = 0
    for col in range(board.shape[1]):
        for row in reversed(range(board.shape[0])):
            if board[row][col] == 1:
                sum_of_heights += row + 1
                break
    num_cleared_rows = np.sum(np.all(board == 1, axis=1))
    # The number of holes - find number of 0s with 1s above
    holes = np.sum((board == 0) & (np.cumsum(board, axis=0) < np.sum(board, axis=0)))
    # print("holes: ", holes)
    # The number of blockades - find number of 1s with 0s above
    blockades = np.sum((board == 1) & (np.cumsum(board, axis=0) > 0))
    # assign higher weights to higher blocks
    weighted_heights = 0
    for col in range(board.shape[1]):
        for row in reversed(range(board.shape[0])):
            # find highest block in each column
            if board[row][col] == 1:
                weighted_heights += (row + 1) * (row + 1)
                break
    # print("weighted heights: ", weighted_heights)
    
    # print board given bottom is index 0
    # for row in reversed(board):
    #     print(row)

    A, B, C, D, E = -1, 10, -20, -1, -1
    score = A * weighted_heights + B * num_cleared_rows + C * holes + D * blockades + E * highest_block_row
    return score

def get_positions(board, rotated_block):
    # print("board: ", board)
    # Return a list of all possible positions for the given block and rotation
    possible_positions = []
    # remove padded 0s from rotated block
    # print("before: ", rotated_block)
    rotated_block = rotated_block[~np.all(rotated_block == 0, axis=1)]
    rotated_block = rotated_block[:, ~np.all(rotated_block == 0, axis=0)]
    # print("after: ", rotated_block)
    # drop block from top for each column - bottom is index 0
    for x in range(board.shape[1] - rotated_block.shape[1] + 1):
        y = board.shape[0] - rotated_block.shape[0] - 1
        while y >= 0:
            if np.any(np.logical_and(rotated_block, board[y:y + rotated_block.shape[0], x:x + rotated_block.shape[1]])):
                if y == board.shape[0] - rotated_block.shape[0] - 1:
                    print("You lose!")
                    break
                possible_positions.append((y + 1, x))
                break
            if y == 0:
                possible_positions.append((y, x))
            y -= 1

    return possible_positions

def clear_full_rows(board):
    full_rows = []
    for y, row in enumerate(board):
        if all(cell == 1 for cell in row):
            full_rows.append(y)
    for row in full_rows:
        board = np.delete(board, row, axis=0)
        board = np.insert(board, board.shape[0], 0, axis=0)
    return board

def find_least_holes(board):
    return np.sum((board == 0) & (np.cumsum(board, axis=0) < np.sum(board, axis=0)))

def find_best_position(board, block_array):
    best_position = None
    best_rotation = None
    best_score = float('-inf')
    board = board.copy()
    least_holes = float('inf')
    for rotation in range(len(block_array[0])):
        positions = get_positions(board, block_array[0][rotation])
        for position in positions:
            new_board = place_block(board, block_array[0][rotation], position)
            new_board = clear_full_rows(new_board)
            # break if have more holes than any before
            if find_least_holes(new_board) > least_holes:
                continue
            least_holes = find_least_holes(new_board)
            least_holes2 = float('inf')
            for rotation2 in range(len(block_array[1])):
                positions2 = get_positions(new_board, block_array[1][rotation2])
                for position2 in positions2:
                    new_board2 = place_block(new_board, block_array[1][rotation2], position2)
                    new_board2 = clear_full_rows(new_board2)
                    # break if have more holes than any before
                    if find_least_holes(new_board2) > least_holes2:
                        continue
                    least_holes2 = find_least_holes(new_board2)
                    for rotation3 in range(len(block_array[2])):
                        positions3 = get_positions(new_board2, block_array[2][rotation3])
                        for position3 in positions3:
                            new_board3 = place_block(new_board2, block_array[2][rotation3], position3)

                            score = evaluate_board(new_board3)
                            if score > best_score:
                                best_position = position
                                best_rotation = rotation
                                best_score = score

    return best_position, best_rotation

def place_block(board, rotated_block, position):
    # print("board: ", board)
    new_board = board.copy()
    # print("new board: ", new_board)
    # remove padded 0s from rotated block
    rotated_block = rotated_block[~np.all(rotated_block == 0, axis=1)]
    rotated_block = rotated_block[:, ~np.all(rotated_block == 0, axis=0)]
    new_board[position[0]:position[0] + rotated_block.shape[0], position[1]:position[1] + rotated_block.shape[1]] += rotated_block
    return new_board

def get_pixel_color(x, y):
    print(f'Getting pixel color at ({x}, {y})')
    color = pyautogui.pixel(x, y)
    return color

def closest_color(pixel, colors):
    pixel_rgb = sRGBColor(*pixel)
    pixel_lab = convert_color(pixel_rgb, LabColor)

    min_diff = float('inf')
    closest_color = None

    for color in colors:
        color_rgb = sRGBColor(*color)
        color_lab = convert_color(color_rgb, LabColor)
        diff = delta_e_cie2000(pixel_lab, color_lab)

        if diff < min_diff:
            min_diff = diff
            closest_color = color

    return closest_color

def get_piece_based_on_color(matched_color):
    piece = None
    if matched_color == (255, 0, 0):
        print('Red - Z')
        piece = tetris_pieces['Z']
    elif matched_color == (0, 255, 0):
        print('Lime - Z2')
        piece = tetris_pieces['Z2']
    elif matched_color == (72, 61, 139):
        print('Dark blue - L2')
        piece = tetris_pieces['L2']
    elif matched_color == (255, 255, 0):
        print('Yellow - O')
        piece = tetris_pieces['O']
    elif matched_color == (64, 224, 204):
        print('Turquoise - I')
        piece = tetris_pieces['I']
    elif matched_color == (255, 165, 0):
        print('Orange - L')
        piece = tetris_pieces['L']
    elif matched_color == (218, 112, 214):
        print('Purple - T')
        piece = tetris_pieces['T']
    if piece is None:
        print('No piece found')
    return piece

# Define your 7 colors
colors = [
    (255, 0, 0),  # red 
    (0, 255, 0),  # lime
    (72, 61, 139), # dark blue
    (255, 255, 0),  # yellow
    (64, 224, 204),  # turquoise
    (255, 165, 0), # orange
    (218, 112, 214), # purple
]

x1, y1 = 0, 0
x2, y2 = 0, 0
# Create a new board
tetrisboard = TetrisBoard()
board_initialized = False
piece_array = []

while True:
    if keyboard.is_pressed('['):
        x1, y1 = mouse.get_position()
        print(f'Coordinates set to ({x1}, {y1})')

    if keyboard.is_pressed(']'):
        x2, y2 = mouse.get_position()
        print(f'Coordinates set to ({x2}, {y2})')

    if x1 != 0 and x2 != 0 and not board_initialized:
        print('Board initialized')
        board_initialized = True
        pixel_color1 = get_pixel_color(x1, y1)
        pixel_color2 = get_pixel_color(x2, y2)
        closest_color1 = closest_color(pixel_color1, colors)
        closest_color2 = closest_color(pixel_color2, colors)
        piece_array.append(get_piece_based_on_color(closest_color1))
        piece_array.append(get_piece_based_on_color(closest_color2))
        while True:
            # set break key
            if keyboard.is_pressed('esc'):
                break
            # if coord at x1, y1 change color, add piece to piece_array
            if closest_color2 != closest_color(get_pixel_color(x2, y2), colors):
                pixel_color2 = get_pixel_color(x2, y2)
                closest_color2 = closest_color(pixel_color2, colors)
                piece_array.append(get_piece_based_on_color(closest_color2))
                # place down the piece in the first array
                best_position, best_rotation = find_best_position(tetrisboard.board, piece_array)
                best_piece_pos_rot = piece_array[0][best_rotation]
                # remove first piece from piece_array
                piece_array.pop(0)
                # remove 0s padding
                best_piece_pos_rot = best_piece_pos_rot[~np.all(best_piece_pos_rot == 0, axis=1)]
                best_piece_pos_rot = best_piece_pos_rot[:, ~np.all(best_piece_pos_rot == 0, axis=0)]
                # add offset depending on padded zeros on the left side of axis 0 only
                offset = 0
                for i in range(best_piece_pos_rot.shape[0]):
                    if np.all(best_piece_pos_rot[i] == 0):
                        offset += 1
                    else:
                        break
                best_position += offset
                # if coord at x2, y2 change color, add piece to piece_array
                # press up arrow to rotate for rotation
                for i in range(best_rotation):
                    pyautogui.press('up')
                    time.sleep(0.1)
                # press left arrow or right arrow to move to position
                if best_position[1] < 3:
                    for i in range(3 - best_position[1]):
                        pyautogui.press('left')
                        time.sleep(0.1)
                elif best_position[1] > 3:
                    for i in range(best_position[1] - 3):
                        pyautogui.press('right')
                        time.sleep(0.1)
                # press space to drop piece
                pyautogui.press('space')
                time.sleep(0.3)
                tetrisboard.add_piece(best_piece_pos_rot, best_position)
                # clear full rows
                tetrisboard.clear_full_rows()
                # print the board
                for row in reversed(tetrisboard.board):
                    print(row)
                print("")


    # Get the pixel color and find the closest color with the "=" key
    if keyboard.is_pressed('='):
        pixel_color1 = get_pixel_color(x1, y1)
        pixel_color2 = get_pixel_color(x2, y2)
        matched_color1 = closest_color(pixel_color1, colors)
        matched_color2 = closest_color(pixel_color2, colors)
        print(f'Pixel color: {pixel_color1}, Closest color: {matched_color1}')
        piece_array = [get_piece_based_on_color(matched_color1), get_piece_based_on_color(matched_color2), get_piece_based_on_color(matched_color3)]
        
        best_position, best_rotation = find_best_position(tetrisboard.board, piece_array)
        best_piece_pos_rot = piece_array[0][best_rotation]
        # remove first piece from piece_array
        piece_array.pop(0)
        # remove 0s padding
        best_piece_pos_rot = best_piece_pos_rot[~np.all(best_piece_pos_rot == 0, axis=1)]
        best_piece_pos_rot = best_piece_pos_rot[:, ~np.all(best_piece_pos_rot == 0, axis=0)]
        tetrisboard.add_piece(piece_array[0][best_rotation], best_position)
        # clear full rows
        tetrisboard.clear_full_rows()
        # press up arrow to rotate for rotation
        for i in range(best_rotation):
            pyautogui.press('up')
        # press left arrow or right arrow to move to position
        if best_position[1] < 5:
            for i in range(5 - best_position[1]):
                pyautogui.press('right')
        elif best_position[1] > 5:
            for i in range(best_position[1] - 5):
                pyautogui.press('left')
        # print the board
        print(tetrisboard.board)

    # Exit the loop with the "ESC" key
    if keyboard.is_pressed('esc'):
        break



# # np.random.seed(1)
# # get 4 random pieces
# piece_array = []
# for i in range(4):
#     piece_array.append(tetris_pieces[list(tetris_pieces.keys())[np.random.randint(0, len(tetris_pieces))]])
# for i in range(200):
#     # random piece
#     # get random piece and append it to piece_array
#     piece_array.append(tetris_pieces[list(tetris_pieces.keys())[np.random.randint(0, len(tetris_pieces))]])
#     # print(list(tetris_pieces.values()))
#     best_position, best_rotation =  find_best_position(tetrisboard.board, piece_array)
#     best_piece_pos_rot = piece_array[0][best_rotation]
#     # remove first piece from piece_array
#     piece_array.pop(0)
#     # remove 0s padding
#     best_piece_pos_rot = best_piece_pos_rot[~np.all(best_piece_pos_rot == 0, axis=1)]
#     best_piece_pos_rot = best_piece_pos_rot[:, ~np.all(best_piece_pos_rot == 0, axis=0)]
#     tetrisboard.add_piece(best_piece_pos_rot, best_position)
#     # clear full rows
#     tetrisboard.clear_full_rows()
#     # print the board
#     for row in reversed(tetrisboard.board):
#         print(row)
#     print("")