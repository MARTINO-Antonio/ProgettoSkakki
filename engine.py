"""
engine.py — logica scacchistica pura, senza I/O.
Espone: init_state, apply_move, generate_moves, king_in_check,
        move_to_san, board_key, check_draw, insufficient_material.
"""
from copy import deepcopy
from collections import Counter

FILES = "abcdefgh"
RANKS = "12345678"


# ── Coordinate ────────────────────────────────────────────────────────────────

def algebraic_to_coord(s):
    return 7 - RANKS.index(s[1]), FILES.index(s[0])

def coord_to_algebraic(r, c):
    return FILES[c] + RANKS[7 - r]

def in_bounds(r, c):
    return 0 <= r < 8 and 0 <= c < 8

def piece_color(p):
    if p == '.': return None
    return 'white' if p.isupper() else 'black'

def opposite(c):
    return 'black' if c == 'white' else 'white'


# ── Stato ─────────────────────────────────────────────────────────────────────

def init_state():
    b = [['.' for _ in range(8)] for _ in range(8)]
    b[0] = list("rnbqkbnr")
    b[1] = list("pppppppp")
    b[6] = list("PPPPPPPP")
    b[7] = list("RNBQKBNR")
    return {
        'board':          b,
        'castle_rights':  {'white': {'K': True, 'Q': True},
                           'black': {'K': True, 'Q': True}},
        'en_passant':     None,
        'halfmove_clock': 0,
    }

def board_key(state):
    """Hash di posizione per la ripetizione triplice."""
    flat = ''.join(''.join(row) for row in state['board'])
    cr   = state['castle_rights']
    ep   = str(state['en_passant'])
    return (f"{flat}|"
            f"{cr['white']['K']}{cr['white']['Q']}"
            f"{cr['black']['K']}{cr['black']['Q']}|{ep}")


# ── Attacco / scacco ──────────────────────────────────────────────────────────

def find_king(board, color):
    k = 'K' if color == 'white' else 'k'
    for r in range(8):
        for c in range(8):
            if board[r][c] == k:
                return r, c
    return None

def is_attacked(board, tr, tc, by):
    # Un pedone bianco si muove verso l'alto (dr=-1) e attacca in diagonale avanti.
    # Per sapere se (tr,tc) è attaccato da un pedone bianco, cerchiamo un pedone
    # bianco nelle caselle da cui potrebbe attaccare (tr,tc): cioè in (tr+1, tc±1).
    # In generale: il pedone attaccante sta a pawn_dir righe SOTTO la casella bersaglio
    # dalla prospettiva del pedone → pawn_dir=+1 per bianco (viene dal basso).
    pawn_dir = 1 if by == 'white' else -1
    pawn     = 'P' if by == 'white' else 'p'
    for dc in (-1, 1):
        r, c = tr + pawn_dir, tc + dc
        if in_bounds(r, c) and board[r][c] == pawn:
            return True
    for dr, dc in [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]:
        r, c = tr + dr, tc + dc
        if in_bounds(r, c) and board[r][c].lower() == 'n' and piece_color(board[r][c]) == by:
            return True
    for dr, dc in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]:
        nr, nc = tr + dr, tc + dc
        first  = True
        while in_bounds(nr, nc):
            p = board[nr][nc]
            if p != '.':
                if piece_color(p) == by:
                    pl = p.lower()
                    if pl == 'q':                            return True
                    if (dr == 0 or dc == 0) and pl == 'r':  return True
                    if (dr != 0 and dc != 0) and pl == 'b': return True
                    if first and pl == 'k':                  return True
                break
            first = False
            nr += dr; nc += dc
    return False

def king_in_check(state, color):
    pos = find_king(state['board'], color)
    if pos is None:
        return True   # re assente = posizione illegale, trattata come scacco
    r, c = pos
    return is_attacked(state['board'], r, c, opposite(color))




# ── Make / Unmake move (senza deepcopy) ───────────────────────────────────────

def make_move(state, move, promotion=None):
    """
    Applica la mossa in-place e restituisce un undo-token per annullarla.
    Usato internamente per evitare deepcopy durante la ricerca.
    """
    board = state['board']
    (r1,c1),(r2,c2) = move
    piece    = board[r1][c1]
    color    = piece_color(piece)
    captured = board[r2][c2]
    is_pawn  = piece.lower() == 'p'

    undo = {
        'move':           move,
        'piece':          piece,
        'captured':       captured,
        'castle_rights':  {'white': dict(state['castle_rights']['white']),
                           'black': dict(state['castle_rights']['black'])},
        'en_passant':     state['en_passant'],
        'halfmove_clock': state['halfmove_clock'],
        'ep_captured':    None,
        'rook_move':      None,
        'promotion':      None,
    }

    # Diritti arrocco per pezzo mosso
    if piece.lower() == 'k':
        state['castle_rights'][color] = {'K': False, 'Q': False}
    if piece.lower() == 'r':
        if (r1,c1)==(7,0): state['castle_rights']['white']['Q']=False
        if (r1,c1)==(7,7): state['castle_rights']['white']['K']=False
        if (r1,c1)==(0,0): state['castle_rights']['black']['Q']=False
        if (r1,c1)==(0,7): state['castle_rights']['black']['K']=False
    if (r2,c2)==(7,0): state['castle_rights']['white']['Q']=False
    if (r2,c2)==(7,7): state['castle_rights']['white']['K']=False
    if (r2,c2)==(0,0): state['castle_rights']['black']['Q']=False
    if (r2,c2)==(0,7): state['castle_rights']['black']['K']=False

    # En passant: rimuovi pedone catturato
    if is_pawn and state['en_passant'] == (r2,c2):
        ep_r = r2 + (1 if color=='white' else -1)
        undo['ep_captured'] = (ep_r, c2, board[ep_r][c2])
        board[ep_r][c2] = '.'

    # Nuovo en passant
    if is_pawn and abs(r2-r1)==2:
        state['en_passant'] = ((r1+r2)//2, c2)
    else:
        state['en_passant'] = None

    # Halfmove clock
    state['halfmove_clock'] = 0 if (is_pawn or captured!='.')                               else state['halfmove_clock'] + 1

    # Muovi pezzo
    board[r2][c2] = piece
    board[r1][c1] = '.'

    # Arrocco: muovi torre
    if piece.lower()=='k' and abs(c2-c1)==2:
        if c2==6:
            undo['rook_move'] = (r2,7,r2,5)
            board[r2][5], board[r2][7] = board[r2][7], '.'
        else:
            undo['rook_move'] = (r2,0,r2,3)
            board[r2][3], board[r2][0] = board[r2][0], '.'

    # Promozione
    if is_pawn and (r2==0 or r2==7) and promotion:
        undo['promotion'] = piece
        board[r2][c2] = promotion if color=='white' else promotion.lower()

    return undo


def unmake_move(state, undo):
    """Annulla la mossa usando il token restituito da make_move."""
    board = state['board']
    (r1,c1),(r2,c2) = undo['move']

    state['castle_rights']['white'] = dict(undo['castle_rights']['white'])
    state['castle_rights']['black'] = dict(undo['castle_rights']['black'])
    state['en_passant']             = undo['en_passant']
    state['halfmove_clock']         = undo['halfmove_clock']

    board[r1][c1] = undo['piece']
    board[r2][c2] = undo['captured']

    if undo['ep_captured']:
        er, ec, ep = undo['ep_captured']
        board[er][ec] = ep

    if undo['rook_move']:
        fr,fc,tr,tc = undo['rook_move']
        board[fr][fc], board[tr][tc] = board[tr][tc], '.'

# ── Generazione mosse ─────────────────────────────────────────────────────────

def piece_moves(state, r, c):
    """Mosse pseudo-legali per il pezzo in (r, c)."""
    board = state['board']
    p     = board[r][c].lower()
    color = piece_color(board[r][c])
    m     = []

    if p == 'p':
        d         = -1 if color == 'white' else 1
        start_row = 6  if color == 'white' else 1
        if in_bounds(r+d, c) and board[r+d][c] == '.':
            m.append(((r,c),(r+d,c)))
            if r == start_row and board[r+2*d][c] == '.':
                m.append(((r,c),(r+2*d,c)))
        for dc in (-1, 1):
            nr, nc = r+d, c+dc
            if in_bounds(nr, nc):
                if board[nr][nc] != '.' and piece_color(board[nr][nc]) != color:
                    m.append(((r,c),(nr,nc)))
                elif state['en_passant'] == (nr, nc):
                    m.append(((r,c),(nr,nc)))

    if p == 'n':
        for dr, dc in [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]:
            nr, nc = r+dr, c+dc
            if in_bounds(nr, nc) and (board[nr][nc]=='.' or piece_color(board[nr][nc])!=color):
                m.append(((r,c),(nr,nc)))

    if p in 'rbq':
        dirs = []
        if p in 'rq': dirs += [(-1,0),(1,0),(0,-1),(0,1)]
        if p in 'bq': dirs += [(-1,-1),(-1,1),(1,-1),(1,1)]
        for dr, dc in dirs:
            nr, nc = r+dr, c+dc
            while in_bounds(nr, nc):
                if board[nr][nc] == '.':
                    m.append(((r,c),(nr,nc)))
                else:
                    if piece_color(board[nr][nc]) != color:
                        m.append(((r,c),(nr,nc)))
                    break
                nr += dr; nc += dc

    if p == 'k':
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr or dc:
                    nr, nc = r+dr, c+dc
                    if in_bounds(nr, nc) and (board[nr][nc]=='.' or piece_color(board[nr][nc])!=color):
                        m.append(((r,c),(nr,nc)))
        row = 7 if color == 'white' else 0
        cr  = state['castle_rights'][color]
        opp = opposite(color)
        # Arrocco solo se il re è sulla sua casella iniziale (e4 o e8)
        if r == row and c == 4 and not king_in_check(state, color):
            if (cr['K'] and board[row][5] == board[row][6] == '.'
                    and not is_attacked(board, row, 5, opp)
                    and not is_attacked(board, row, 6, opp)):
                m.append(((r,c),(row,6)))
            if (cr['Q'] and board[row][1] == board[row][2] == board[row][3] == '.'
                    and not is_attacked(board, row, 3, opp)
                    and not is_attacked(board, row, 2, opp)):
                m.append(((r,c),(row,2)))
    return m

def generate_moves(state, color):
    """Restituisce tutte le mosse legali per il colore dato."""
    pseudo = []
    for r in range(8):
        for c in range(8):
            if piece_color(state['board'][r][c]) == color:
                pseudo += piece_moves(state, r, c)
    legal = []
    for mv in pseudo:
        undo = make_move(state, mv)
        if not king_in_check(state, color):
            legal.append(mv)
        unmake_move(state, undo)
    return legal


# ── Applica mossa ─────────────────────────────────────────────────────────────

def apply_move(state, move, promotion=None):
    """
    Applica la mossa allo stato in-place e lo restituisce.
    promotion: 'Q' | 'R' | 'B' | 'N'  (maiuscolo; il caso viene adattato al colore)
    """
    board = state['board']
    (r1, c1), (r2, c2) = move
    piece      = board[r1][c1]
    color      = piece_color(piece)
    is_capture = board[r2][c2] != '.'
    is_pawn    = piece.lower() == 'p'

    # Aggiorna diritti arrocco per il pezzo mosso
    if piece.lower() == 'k':
        state['castle_rights'][color] = {'K': False, 'Q': False}
    if piece.lower() == 'r':
        if (r1,c1) == (7,0): state['castle_rights']['white']['Q'] = False
        if (r1,c1) == (7,7): state['castle_rights']['white']['K'] = False
        if (r1,c1) == (0,0): state['castle_rights']['black']['Q'] = False
        if (r1,c1) == (0,7): state['castle_rights']['black']['K'] = False
    # Aggiorna diritti arrocco per la torre eventualmente catturata
    if (r2,c2) == (7,0): state['castle_rights']['white']['Q'] = False
    if (r2,c2) == (7,7): state['castle_rights']['white']['K'] = False
    if (r2,c2) == (0,0): state['castle_rights']['black']['Q'] = False
    if (r2,c2) == (0,7): state['castle_rights']['black']['K'] = False

    # En passant: rimuovi il pedone catturato
    if is_pawn and state['en_passant'] == (r2, c2):
        ep_r = r2 + (1 if color == 'white' else -1)
        board[ep_r][c2] = '.'
        is_capture = True

    # Imposta nuova casella en passant
    if is_pawn and abs(r2 - r1) == 2:
        state['en_passant'] = ((r1 + r2) // 2, c2)
    else:
        state['en_passant'] = None

    # Halfmove clock
    state['halfmove_clock'] = 0 if (is_pawn or is_capture) else state['halfmove_clock'] + 1

    # Muovi il pezzo
    board[r2][c2] = piece
    board[r1][c1] = '.'

    # Arrocco: sposta la torre
    if piece.lower() == 'k' and abs(c2 - c1) == 2:
        if c2 == 6: board[r2][5], board[r2][7] = board[r2][7], '.'
        else:       board[r2][3], board[r2][0] = board[r2][0], '.'

    # Promozione
    if is_pawn and (r2 == 0 or r2 == 7) and promotion:
        board[r2][c2] = promotion if color == 'white' else promotion.lower()

    return state


# ── Notazione SAN ─────────────────────────────────────────────────────────────

def move_to_san(state, move, legal_moves, promotion=None):
    """Converte una mossa in notazione algebrica standard."""
    board  = state['board']
    (r1,c1),(r2,c2) = move
    piece  = board[r1][c1]
    pl     = piece.lower()
    color  = piece_color(piece)
    is_cap = board[r2][c2] != '.' or (pl == 'p' and state['en_passant'] == (r2,c2))

    # Arrocco
    if pl == 'k' and abs(c2 - c1) == 2:
        base = 'O-O' if c2 == 6 else 'O-O-O'
    elif pl == 'p':
        base = ''
        if is_cap:
            base += FILES[c1] + 'x'
        base += coord_to_algebraic(r2, c2)
        if promotion:
            base += '=' + promotion.upper()
    else:
        base = piece.upper()
        # Disambiguazione
        ambiguous = [mv for mv in legal_moves
                     if mv[1] == (r2,c2) and mv[0] != (r1,c1)
                     and board[mv[0][0]][mv[0][1]].lower() == pl]
        if ambiguous:
            same_col = any(mv[0][1] == c1 for mv in ambiguous)
            same_row = any(mv[0][0] == r1 for mv in ambiguous)
            if not same_col:       base += FILES[c1]
            elif not same_row:     base += RANKS[7 - r1]
            else:                  base += FILES[c1] + RANKS[7 - r1]
        if is_cap: base += 'x'
        base += coord_to_algebraic(r2, c2)

    # Simbolo scacco / matto
    ns        = apply_move(deepcopy(state), move, promotion)
    opp       = opposite(color)
    opp_legal = generate_moves(ns, opp)
    if king_in_check(ns, opp):
        base += '#' if not opp_legal else '+'

    return base


# ── Patta ─────────────────────────────────────────────────────────────────────

def insufficient_material(board):
    pieces = {'white': [], 'black': []}
    bishops = {'white': [], 'black': []}
    for r in range(8):
        for c in range(8):
            p = board[r][c]
            if p == '.': continue
            col = piece_color(p)
            pieces[col].append(p.lower())
            if p.lower() == 'b':
                bishops[col].append((r + c) % 2)  # 0=chiaro, 1=scuro

    def weak(ps):
        s = sorted(ps)
        return s in [['k'], ['b','k'], ['k','n']]

    if not (weak(pieces['white']) and weak(pieces['black'])):
        return False

    # K+B vs K+B: patta solo se gli alfieri sono sullo stesso colore di casella
    if sorted(pieces['white']) == ['b','k'] and sorted(pieces['black']) == ['b','k']:
        return bishops['white'][0] == bishops['black'][0]

    return True

def check_draw(state, position_history):
    if state['halfmove_clock'] >= 100:
        return "Regola delle 50 mosse"
    if insufficient_material(state['board']):
        return "Materiale insufficiente"
    if position_history[board_key(state)] >= 3:
        return "Ripetizione triplice"
    return None
