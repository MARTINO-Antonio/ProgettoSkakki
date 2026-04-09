"""
ai.py — motore AI con minimax, alpha-beta pruning e ottimizzazioni.

  - Make/unmake move invece di deepcopy → 4-10x più veloce
  - Iterative deepening con time limit di sicurezza (no blocchi infiniti)
  - Transposition table (TT) → evita di ricalcolare posizioni già viste
  - Killer moves → migliora l'ordinamento delle mosse silenziose
  - Fallback assoluto: choose_move non restituisce mai None se esistono mosse
"""
import time
from engine import (generate_moves, apply_move, king_in_check,
                    piece_color, opposite, find_king, board_key,
                    make_move, unmake_move)
from openings import book_move

# ── Valori materiali ──────────────────────────────────────────────────────────

MATERIAL = {'p': 100, 'n': 320, 'b': 330, 'r': 500, 'q': 900, 'k': 20000}

# ── Piece-square tables ───────────────────────────────────────────────────────

PST = {
    'p': [
         0,  0,  0,  0,  0,  0,  0,  0,
        50, 50, 50, 50, 50, 50, 50, 50,
        10, 10, 20, 30, 30, 20, 10, 10,
         5,  5, 10, 25, 25, 10,  5,  5,
         0,  0,  0, 20, 20,  0,  0,  0,
         5, -5,-10,  0,  0,-10, -5,  5,
         5, 10, 10,-20,-20, 10, 10,  5,
         0,  0,  0,  0,  0,  0,  0,  0,
    ],
    'n': [
        -50,-40,-30,-30,-30,-30,-40,-50,
        -40,-20,  0,  0,  0,  0,-20,-40,
        -30,  0, 10, 15, 15, 10,  0,-30,
        -30,  5, 15, 20, 20, 15,  5,-30,
        -30,  0, 15, 20, 20, 15,  0,-30,
        -30,  5, 10, 15, 15, 10,  5,-30,
        -40,-20,  0,  5,  5,  0,-20,-40,
        -50,-40,-30,-30,-30,-30,-40,-50,
    ],
    'b': [
        -20,-10,-10,-10,-10,-10,-10,-20,
        -10,  0,  0,  0,  0,  0,  0,-10,
        -10,  0,  5, 10, 10,  5,  0,-10,
        -10,  5,  5, 10, 10,  5,  5,-10,
        -10,  0, 10, 10, 10, 10,  0,-10,
        -10, 10, 10, 10, 10, 10, 10,-10,
        -10,  5,  0,  0,  0,  0,  5,-10,
        -20,-10,-10,-10,-10,-10,-10,-20,
    ],
    'r': [
         0,  0,  0,  0,  0,  0,  0,  0,
         5, 10, 10, 10, 10, 10, 10,  5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
         0,  0,  0,  5,  5,  0,  0,  0,
    ],
    'q': [
        -20,-10,-10, -5, -5,-10,-10,-20,
        -10,  0,  0,  0,  0,  0,  0,-10,
        -10,  0,  5,  5,  5,  5,  0,-10,
         -5,  0,  5,  5,  5,  5,  0, -5,
          0,  0,  5,  5,  5,  5,  0, -5,
        -10,  5,  5,  5,  5,  5,  0,-10,
        -10,  0,  5,  0,  0,  0,  0,-10,
        -20,-10,-10, -5, -5,-10,-10,-20,
    ],
    'k_mid': [
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -20,-30,-30,-40,-40,-30,-30,-20,
        -10,-20,-20,-20,-20,-20,-20,-10,
         20, 20,  0,  0,  0,  0, 20, 20,
         20, 30, 10,  0,  0, 10, 30, 20,
    ],
    'k_end': [
        -50,-40,-30,-20,-20,-30,-40,-50,
        -30,-20,-10,  0,  0,-10,-20,-30,
        -30,-10, 20, 30, 30, 20,-10,-30,
        -30,-10, 30, 40, 40, 30,-10,-30,
        -30,-10, 30, 40, 40, 30,-10,-30,
        -30,-10, 20, 30, 30, 20,-10,-30,
        -30,-30,  0,  0,  0,  0,-30,-30,
        -50,-30,-30,-30,-30,-30,-30,-50,
    ],
}

def pst_value(piece, r, c, endgame=False):
    pl = piece.lower()
    if pl == 'k':
        table = PST['k_end'] if endgame else PST['k_mid']
    elif pl in PST:
        table = PST[pl]
    else:
        return 0
    idx = r * 8 + c if piece.isupper() else (7 - r) * 8 + c
    return table[idx]

def is_endgame(board):
    queens = sum(1 for row in board for p in row if p.lower() == 'q')
    minors = sum(1 for row in board for p in row
                 if p.lower() in ('n', 'b', 'r') and p != '.')
    return queens == 0 or (queens <= 2 and minors <= 2)


# ── Valutazione statica ───────────────────────────────────────────────────────

def evaluate(state):
    board   = state['board']
    endgame = is_endgame(board)
    score   = 0
    for r in range(8):
        for c in range(8):
            p = board[r][c]
            if p == '.':
                continue
            pl  = p.lower()
            val = MATERIAL[pl] + pst_value(p, r, c, endgame)
            score += val if p.isupper() else -val
    return score


# ── Ordinamento mosse ─────────────────────────────────────────────────────────

def move_score(board, move, killers=None, tt_move=None):
    if tt_move and move == tt_move:
        return 20000
    (r1,c1),(r2,c2) = move
    victim   = board[r2][c2]
    attacker = board[r1][c1]
    if victim != '.':
        return 10000 + 10 * MATERIAL[victim.lower()] - MATERIAL[attacker.lower()]
    if killers and move in killers:
        return 5000
    return 0

def ordered_moves(state, moves, killers=None, tt_move=None):
    board = state['board']
    return sorted(moves,
                  key=lambda m: move_score(board, m, killers, tt_move),
                  reverse=True)


# ── Transposition Table ───────────────────────────────────────────────────────

TT_EXACT = 0
TT_LOWER = 1
TT_UPPER = 2

_tt = {}

def tt_lookup(key, depth, alpha, beta):
    entry = _tt.get(key)
    if not entry:
        return None
    e_depth, e_flag, e_score, e_move = entry
    if e_depth < depth:
        return None
    if e_flag == TT_EXACT:
        return e_score, e_move
    if e_flag == TT_LOWER and e_score >= beta:
        return e_score, e_move
    if e_flag == TT_UPPER and e_score <= alpha:
        return e_score, e_move
    return None

def tt_store(key, depth, flag, score, move):
    _tt[key] = (depth, flag, score, move)


# ── Minimax con alpha-beta ────────────────────────────────────────────────────

INF = 10_000_000

def minimax(state, depth, alpha, beta, maximizing, killers, deadline):
    if time.time() >= deadline:
        return evaluate(state), None

    color = 'white' if maximizing else 'black'
    key   = board_key(state) + ('w' if maximizing else 'b')

    tt_result = tt_lookup(key, depth, alpha, beta)
    if tt_result is not None:
        return tt_result

    moves = generate_moves(state, color)

    if not moves:
        if king_in_check(state, color):
            score = (-INF - depth) if maximizing else (INF + depth)
        else:
            score = 0
        tt_store(key, depth, TT_EXACT, score, None)
        return score, None

    if depth == 0:
        score = evaluate(state)
        tt_store(key, depth, TT_EXACT, score, None)
        return score, None

    tt_entry  = _tt.get(key)
    tt_move   = tt_entry[3] if tt_entry else None
    ply_kils  = killers[depth] if depth < len(killers) else None
    moves     = ordered_moves(state, moves, ply_kils, tt_move)

    best_move  = moves[0]
    orig_alpha = alpha

    if maximizing:
        best = -INF
        for mv in moves:
            if time.time() >= deadline:
                break
            promo = _auto_promo(state, mv, 'white')
            undo  = make_move(state, mv, promo)
            score, _ = minimax(state, depth - 1, alpha, beta, False, killers, deadline)
            unmake_move(state, undo)
            if score > best:
                best, best_move = score, mv
            alpha = max(alpha, best)
            if beta <= alpha:
                _add_killer(killers, depth, state, mv)
                break
        flag = TT_EXACT if orig_alpha < best < beta else \
               (TT_LOWER if best >= beta else TT_UPPER)
        tt_store(key, depth, flag, best, best_move)
        return best, best_move
    else:
        best = INF
        for mv in moves:
            if time.time() >= deadline:
                break
            promo = _auto_promo(state, mv, 'black')
            undo  = make_move(state, mv, promo)
            score, _ = minimax(state, depth - 1, alpha, beta, True, killers, deadline)
            unmake_move(state, undo)
            if score < best:
                best, best_move = score, mv
            beta = min(beta, best)
            if beta <= alpha:
                _add_killer(killers, depth, state, mv)
                break
        flag = TT_EXACT if orig_alpha < best < beta else \
               (TT_LOWER if best >= beta else TT_UPPER)
        tt_store(key, depth, flag, best, best_move)
        return best, best_move


def _auto_promo(state, mv, color):
    piece = state['board'][mv[0][0]][mv[0][1]]
    if piece.lower() == 'p' and (mv[1][0] == 0 or mv[1][0] == 7):
        return 'Q' if color == 'white' else 'q'
    return None

def _add_killer(killers, depth, state, mv):
    if depth >= len(killers):
        return
    if state['board'][mv[1][0]][mv[1][1]] == '.':
        killers[depth].add(mv)
        if len(killers[depth]) > 2:
            killers[depth].pop()


# ── Time limits per difficoltà ────────────────────────────────────────────────

TIME_LIMITS = {
    1: 0.5,    # Facile
    3: 15.0,   # Medio     — può pensare quanto serve, max 15s
    4: 60.0,   # Difficile — può pensare quanto serve, max 60s
}


# ── Punto di ingresso ─────────────────────────────────────────────────────────

def choose_move(state, color, depth=3, move_history=None):
    """
    Restituisce (mossa, nome_apertura_o_None).
    Garantisce di non restituire mai None come mossa se esistono mosse legali.
    Usa iterative deepening con time limit per non superare mai TIME_LIMITS[depth].
    """
    global _tt
    _tt = {}

    # Libro aperture
    if move_history is not None:
        mv, opening_name = book_move(move_history)
        if mv is not None:
            legal = generate_moves(state, color)
            if mv in legal:
                return mv, opening_name

    legal = generate_moves(state, color)
    if not legal:
        return None, None

    maximizing = (color == 'white')
    time_limit = TIME_LIMITS.get(depth, 2.0)
    deadline   = time.time() + time_limit
    killers    = [set() for _ in range(depth + 2)]

    # Fallback assoluto: anche se il tempo scade al primo nodo, ritorniamo qualcosa
    best_move  = legal[0]

    # Iterative deepening: ogni iterazione affina la risposta
    for current_depth in range(1, depth + 1):
        if time.time() >= deadline:
            break
        _, mv = minimax(state, current_depth, -INF, INF,
                        maximizing, killers, deadline)
        if mv is not None:
            best_move = mv

    return best_move, None
