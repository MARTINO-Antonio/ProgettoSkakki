#!/usr/bin/env python3
"""
chess.py — interfaccia terminale.
Dipende da engine.py e ai.py nella stessa cartella.

Avvio:
    python chess.py          → scelta modalità all'avvio
    python chess.py --white  → giochi col bianco contro AI
    python chess.py --black  → giochi col nero contro AI
    python chess.py --2p     → due giocatori umani
"""
import os
import sys
import time
import argparse
from copy import deepcopy
from collections import Counter

from engine import (
    FILES, RANKS,
    init_state, board_key, apply_move, generate_moves,
    king_in_check, find_king, piece_color, opposite,
    algebraic_to_coord, coord_to_algebraic,
    move_to_san, check_draw,
)
from ai import choose_move

# ── ANSI ──────────────────────────────────────────────────────────────────────

RESET          = "\033[0m"
GREEN_BG       = "\033[42m"
GREEN_LIGHT_BG = "\033[102m"
RED_BG         = "\033[41m"
YELLOW_BG      = "\033[43m"
BLACK_FG       = "\033[30m"
BOLD           = "\033[1m"
DIM            = "\033[2m"
CYAN           = "\033[36m"
YELLOW         = "\033[33m"
RED            = "\033[31m"
GREEN          = "\033[32m"
MAGENTA        = "\033[35m"

UNICODE = {
    'K':'♔','Q':'♕','R':'♖','B':'♗','N':'♘','P':'♙',
    'k':'♚','q':'♛','r':'♜','b':'♝','n':'♞','p':'♟',
    '.':' ',
}

MAT = {'p':1,'n':3,'b':3,'r':5,'q':9,'k':0}

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


# ── Visualizzazione ───────────────────────────────────────────────────────────

def cell(s, bg=None):
    if bg:
        return f"{bg}{BLACK_FG} {s} {RESET}"
    return f" {s} "

def material_balance(board):
    score = 0
    for row in board:
        for p in row:
            if p == '.': continue
            v = MAT[p.lower()]
            score += v if p.isupper() else -v
    if score == 0:
        return 0, f"{DIM}={RESET}"
    color = GREEN if score > 0 else RED
    sign  = '+' if score > 0 else ''
    return score, f"{color}{BOLD}{sign}{score}♙{RESET}"

def format_move_log(move_log, max_rows=8):
    pairs = []
    for i in range(0, len(move_log), 2):
        w   = move_log[i]
        b   = move_log[i+1] if i+1 < len(move_log) else ''
        num = i // 2 + 1
        pairs.append(f"{DIM}{num:2}.{RESET} {BOLD}{w:<8}{RESET} {b}")
    visible = pairs[-max_rows:] if len(pairs) > max_rows else pairs
    while len(visible) < max_rows:
        visible.append('')
    return visible

def print_board(state, highlights=None, selected=None, turn=None,
                last_move=None, move_log=None, message=None, ai_color=None):
    board      = state['board']
    highlights = highlights or {}
    last_sqs   = set()
    if last_move:
        last_sqs.add(last_move[0])
        last_sqs.add(last_move[1])

    check_pos = None
    if turn and king_in_check(state, turn):
        check_pos = find_king(board, turn)

    log_lines  = format_move_log(move_log or [], max_rows=8)
    log_header = f"  {DIM}{'#':>3}  {'Bianco':<10} Nero{RESET}"
    _, bal_str = material_balance(board)

    print()
    print(f"    a   b   c   d   e   f   g   h       {log_header}")
    print(f"  ┌" + "───┬"*7 + "───┐")

    for r in range(8):
        print(f"{8-r} │", end="")
        for c in range(8):
            piece = UNICODE[board[r][c]]
            if selected == (r, c):
                print(cell(piece, GREEN_BG), end="│")
            elif (r, c) in highlights:
                print(cell(highlights[(r,c)], GREEN_LIGHT_BG), end="│")
            elif check_pos == (r, c):
                print(cell(piece, RED_BG), end="│")
            elif (r, c) in last_sqs:
                print(cell(piece, YELLOW_BG), end="│")
            else:
                print(cell(piece), end="│")

        log_line = log_lines[r] if r < len(log_lines) else ''
        suffix   = f"   {bal_str}" if r == 4 else ''
        print(f" {8-r}   {log_line}{suffix}")

        if r < 7:
            print("  ├" + "───┼"*7 + "───┤")

    print("  └" + "───┴"*7 + "───┘")
    print(f"    a   b   c   d   e   f   g   h\n")

    if message:
        print(message)


# ── Promozione ────────────────────────────────────────────────────────────────

def parse_promotion(cmd):
    if len(cmd) == 5 and cmd[4] in 'qrbn':
        return cmd[4].upper()
    return None

def ask_promotion():
    while True:
        ch = input(f"  {CYAN}Promozione (Q/R/B/N):{RESET} ").strip().upper()
        if ch in ('Q','R','B','N'):
            return ch
        print("  Scelta non valida.")


# ── Scelta modalità ───────────────────────────────────────────────────────────

def choose_mode():
    print(f"\n  {BOLD}♟  Scacchi{RESET}\n")
    print(f"  {CYAN}1{RESET}  Due giocatori")
    print(f"  {CYAN}2{RESET}  Gioca col Bianco contro AI")
    print(f"  {CYAN}3{RESET}  Gioca col Nero contro AI")
    print(f"  {CYAN}4{RESET}  AI vs AI  (spettatore)\n")
    while True:
        ch = input("  Scelta> ").strip()
        if ch == '1': return None
        if ch == '2': return 'black'
        if ch == '3': return 'white'
        if ch == '4': return 'both'
        print("  Scelta non valida.")

DIFFICULTY = {'1': 1, '2': 3, '3': 4}

def choose_depth():
    print(f"\n  {DIM}Difficoltà AI:{RESET}")
    print(f"  {CYAN}1{RESET}  Facile")
    print(f"  {CYAN}2{RESET}  Medio")
    print(f"  {CYAN}3{RESET}  Difficile\n")
    while True:
        ch = input("  Scelta> ").strip()
        if ch in DIFFICULTY:
            return DIFFICULTY[ch]
        print("  Scelta non valida.")


# ── Esecuzione mossa ──────────────────────────────────────────────────────────

def do_move(state, mv, promo, turn, legal,
            history, move_log, position_history, last_move):
    san = move_to_san(state, mv, legal, promo)
    history.append((deepcopy(state), turn, last_move, list(move_log)))
    position_history[board_key(state)] -= 1
    state     = apply_move(state, mv, promo)
    last_move = (mv[0], mv[1])
    move_log.append(san)
    position_history[board_key(state)] += 1
    return state, last_move


# ── Main loop ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--white', action='store_true')
    parser.add_argument('--black', action='store_true')
    parser.add_argument('--2p',    action='store_true', dest='twop')
    args, _ = parser.parse_known_args()

    clear_screen()

    if args.twop:
        ai_color, depth = None, 3
    elif args.white:
        ai_color, depth = 'black', 3
    elif args.black:
        ai_color, depth = 'white', 3
    else:
        ai_color = choose_mode()
        depth    = choose_depth() if ai_color else 3

    state             = init_state()
    turn              = 'white'
    selected          = None
    history           = []
    last_move         = None
    move_log          = []
    position_history  = Counter()
    pending_draw_from = None
    message           = None
    move_history      = []   # lista mosse come tuple per libro aperture
    current_opening   = None # nome apertura corrente

    position_history[board_key(state)] += 1

    HELP = f"""
  {BOLD}Comandi:{RESET}
    {CYAN}e2{RESET}       seleziona il pezzo in e2
    {CYAN}e4{RESET}       (dopo selezione) muovi nella casella
    {CYAN}e2e4{RESET}     mossa diretta
    {CYAN}e7e8q{RESET}    promozione inline (q/r/b/n)
    {CYAN}u{RESET}        annulla ultima mossa  {"(annulla anche la mossa AI)" if ai_color and ai_color != 'both' else ""}
    {CYAN}draw{RESET}     proponi patta
    {CYAN}hint{RESET}     suggerimento AI{"" if ai_color and ai_color != 'both' else " (non disponibile)"}
    {CYAN}help{RESET}     mostra questi comandi
    {CYAN}quit{RESET}     esci
"""

    while True:
        legal = generate_moves(state, turn)

        # ── Fine partita ──
        if not legal:
            clear_screen()
            print_board(state, turn=turn, last_move=last_move,
                        move_log=move_log, ai_color=ai_color)
            if king_in_check(state, turn):
                winner = 'Bianco' if turn == 'black' else 'Nero'
                print(f"  {BOLD}{GREEN}Scacco matto! Vince il {winner}.{RESET}\n")
            else:
                print(f"  {BOLD}{YELLOW}Stallo! Patta.{RESET}\n")
            input("  (invio per uscire)")
            break

        draw_reason = check_draw(state, position_history)
        if draw_reason:
            clear_screen()
            print_board(state, turn=turn, last_move=last_move,
                        move_log=move_log, ai_color=ai_color)
            print(f"  {BOLD}{YELLOW}Patta per {draw_reason}.{RESET}\n")
            input("  (invio per uscire)")
            break

        # ── Turno AI ──
        is_ai_turn = (ai_color == 'both') or (ai_color == turn)
        if is_ai_turn:
            # Se l'umano ha proposto patta, l'AI risponde prima di muovere
            if pending_draw_from and pending_draw_from != turn:
                from ai import evaluate as ai_evaluate
                score = ai_evaluate(state)
                # L'AI accetta se è in svantaggio (>= 1 pedone), altrimenti rifiuta
                ai_losing = (turn == 'white' and score < -80) or (turn == 'black' and score > 80)
                clear_screen()
                print_board(state, {}, None, turn, last_move, move_log,
                            ai_color=ai_color)
                if ai_losing:
                    print(f"  {MAGENTA}AI accetta la patta.{RESET}\n")
                    input("  (invio per uscire)")
                    break
                else:
                    message = f"{MAGENTA}AI rifiuta la patta.{RESET}"
                    pending_draw_from = None
                    continue

            clear_screen()
            print_board(state, {}, None, turn, last_move, move_log,
                        message=f"  {MAGENTA}AI ({turn}) sta pensando...{RESET}",
                        ai_color=ai_color)

            mv, opening_name = choose_move(state, turn, depth, move_history)
            if mv is None:
                # Sicurezza: non dovrebbe accadere (legal != [] è già verificato sopra)
                continue
            if opening_name:
                current_opening = opening_name

            # Determina promozione AI (sempre regina)
            promo = None
            src_p = state['board'][mv[0][0]][mv[0][1]]
            if src_p.lower() == 'p' and (mv[1][0] == 0 or mv[1][0] == 7):
                promo = 'Q' if turn == 'white' else 'q'

            move_history.append(mv)
            state, last_move = do_move(
                state, mv, promo, turn, legal,
                history, move_log, position_history, last_move)
            turn = opposite(turn)
            selected = None
            pending_draw_from = None

            if ai_color == 'both':
                time.sleep(0.5)
            continue

        # ── Highlights ──
        highlights = {}
        if selected:
            for mv in legal:
                if mv[0] == selected:
                    r, c = mv[1]
                    highlights[(r,c)] = "✖" if state['board'][r][c] != '.' else "·"

        # ── Stampa scacchiera ──
        clear_screen()
        turn_label = f"{BOLD}{'Bianco' if turn == 'white' else 'Nero'}{RESET}"
        status = ''
        if king_in_check(state, turn):
            status = f"{RED}{BOLD}Scacco!{RESET}"
        elif pending_draw_from and pending_draw_from != turn:
            status = f"{YELLOW}L'avversario propone patta. (draw/no){RESET}"
        elif pending_draw_from and pending_draw_from == turn:
            status = f"{DIM}Patta proposta, in attesa di risposta...{RESET}"
        elif message:
            status = message
            message = None

        opening_line = f"  {DIM}Apertura: {current_opening}{RESET}\n" if current_opening else ""
        print_board(state, highlights, selected, turn, last_move, move_log,
                    message=(opening_line + (f"  Turno: {turn_label}   {status}"
                             if status else f"  Turno: {turn_label}")),
                    ai_color=ai_color)

        cmd = input(f"  {turn}> ").strip().lower()

        if cmd == 'help':
            print(HELP); input("  (invio per continuare)"); continue

        if cmd in ('exit', 'quit'):
            break

        if cmd in ('u', 'undo'):
            if history:
                steps = 2 if (ai_color and ai_color != 'both' and len(history) >= 2) else 1
                for _ in range(steps):
                    if history:
                        state, turn, last_move, move_log = history.pop()
                        position_history[board_key(state)] += 1
                        if move_history: move_history.pop()
                selected = None; pending_draw_from = None
                current_opening = None
            else:
                message = f"{DIM}Nessuna mossa da annullare.{RESET}"
            continue

        if cmd == 'draw':
            if pending_draw_from == opposite(turn):
                clear_screen()
                print_board(state, turn=turn, last_move=last_move,
                            move_log=move_log, ai_color=ai_color)
                print(f"  {BOLD}{YELLOW}Patta concordata.{RESET}\n")
                input("  (invio per uscire)")
                break
            else:
                pending_draw_from = turn
                message = f"{YELLOW}Patta proposta. L'avversario risponda 'draw'.{RESET}"
            continue

        if cmd == 'no':
            pending_draw_from = None
            message = f"{DIM}Proposta rifiutata.{RESET}"
            continue

        if cmd == 'hint':
            if ai_color and ai_color != 'both':
                mv_h, _ = choose_move(state, turn, depth, move_history)
                if mv_h:
                    s = coord_to_algebraic(*mv_h[0])
                    d = coord_to_algebraic(*mv_h[1])
                    message = f"{DIM}Suggerimento AI: {CYAN}{s}{d}{RESET}"
            else:
                message = f"{DIM}Hint disponibile solo in modalità vs AI.{RESET}"
            continue

        # ── Destinazione dopo selezione ──
        if selected and len(cmd) == 2 and cmd[0] in FILES and cmd[1] in RANKS:
            dst     = algebraic_to_coord(cmd)
            matched = [mv for mv in legal if mv[0] == selected and mv[1] == dst]
            if matched:
                mv    = matched[0]
                r, c  = dst
                promo = None
                if state['board'][selected[0]][selected[1]].lower() == 'p' and (r == 0 or r == 7):
                    promo = ask_promotion()
                move_history.append(mv)
                state, last_move = do_move(
                    state, mv, promo, turn, legal,
                    history, move_log, position_history, last_move)
                turn = opposite(turn); selected = None; pending_draw_from = None
            else:
                sq = algebraic_to_coord(cmd)
                if piece_color(state['board'][sq[0]][sq[1]]) == turn:
                    selected = sq
                else:
                    message = f"{DIM}Destinazione non valida.{RESET}"
            continue

        # ── Selezione casella ──
        if len(cmd) == 2 and cmd[0] in FILES and cmd[1] in RANKS:
            sq = algebraic_to_coord(cmd)
            if piece_color(state['board'][sq[0]][sq[1]]) == turn:
                selected = sq
            else:
                message = f"{DIM}Non è un tuo pezzo.{RESET}"
            continue

        # ── Mossa diretta ──
        if (len(cmd) in (4, 5) and cmd[0] in FILES and cmd[1] in RANKS
                and cmd[2] in FILES and cmd[3] in RANKS):
            try:
                src   = algebraic_to_coord(cmd[:2])
                dst   = algebraic_to_coord(cmd[2:4])
                mv    = (src, dst)
                promo = parse_promotion(cmd)
                if mv in legal:
                    r, c = dst
                    if (state['board'][src[0]][src[1]].lower() == 'p'
                            and (r == 0 or r == 7) and not promo):
                        promo = ask_promotion()
                    move_history.append(mv)
                    state, last_move = do_move(
                        state, mv, promo, turn, legal,
                        history, move_log, position_history, last_move)
                    turn = opposite(turn); selected = None; pending_draw_from = None
                else:
                    message = f"{DIM}Mossa illegale.{RESET}"
            except (ValueError, IndexError):
                message = f"{DIM}Formato non valido.{RESET}"
            continue

        message = f"{DIM}Input non riconosciuto. Scrivi 'help'.{RESET}"


if __name__ == "__main__":
    main()
