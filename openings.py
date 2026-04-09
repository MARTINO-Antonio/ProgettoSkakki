"""
openings.py — libro delle aperture.

Struttura: ogni apertura è una lista di mosse in notazione long algebraic
(es. "e2e4"). Il libro viene indicizzato per prefisso di sequenza: dato
lo storico delle mosse giocate, si cercano tutte le continuazioni note
e se ne sceglie una a caso (con peso) per dare varietà.

Aperture incluse (con varianti principali):
  Gioco aperto (1.e4 e5):
    - Apertura Italiana / Giuoco Piano
    - Apertura Italiana / Attacco Evans
    - Apertura Spagnola (Ruy López) — variante chiusa e variante aperta
    - Apertura Scozzese
    - Gambetto di Re (accettato e rifiutato)
    - Apertura dei Quattro Cavalli

  Difesa Siciliana (1.e4 c5):
    - Variante Najdorf
    - Variante del Drago
    - Variante Classica
    - Variante Scheveningen
    - Variante Kan

  Gioco di donna (1.d4 d5):
    - Gambetto di Donna Accettato (QGA)
    - Gambetto di Donna Rifiutato (QGD) — variante ortodossa
    - Difesa Slava
    - Difesa Semi-Slava

  Difese indiane (1.d4 Nf6):
    - Difesa Indiana di Re (KID) — variante classica
    - Difesa Nimzo-Indiana
    - Difesa Grünfeld
    - Difesa Indiana di Donna (QID)
    - Difesa Olandese

  Aperture di fianchetto (1.Nf3 / 1.c4 / 1.g3):
    - Sistema Londinese
    - Apertura Inglese
    - Apertura Reti
    - Apertura Catalana

  Altre:
    - Difesa Francese — variante d'avanzata e variante Winawer
    - Difesa Caro-Kann — variante classica
    - Difesa Pirc / Moderna
    - Apertura Ponziani
    - Gambetto di Budapest
"""

import random
from engine import algebraic_to_coord, apply_move, init_state

# ── Definizione aperture ──────────────────────────────────────────────────────
# Formato: lista di (nome, [mosse in long algebraic])
# Le sequenze possono essere di lunghezza variabile.

OPENINGS_RAW = [

    # ── GIOCO APERTO 1.e4 e5 ─────────────────────────────────────────────────

    ("Apertura Italiana — Giuoco Piano", [
        "e2e4","e7e5","g1f3","b8c6","f1c4","f8c5","c2c3","g8f6","d2d3",
    ]),
    ("Apertura Italiana — Giuoco Pianissimo", [
        "e2e4","e7e5","g1f3","b8c6","f1c4","f8c5","d2d3","g8f6","c2c3",
    ]),
    ("Apertura Italiana — Attacco Evans", [
        "e2e4","e7e5","g1f3","b8c6","f1c4","f8c5","b2b4","c5b4","c2c3",
    ]),
    ("Apertura Italiana — Variante dei Due Cavalli", [
        "e2e4","e7e5","g1f3","b8c6","f1c4","g8f6","d2d4",
    ]),

    ("Apertura Spagnola — Variante Chiusa", [
        "e2e4","e7e5","g1f3","b8c6","f1b5","a7a6","b5a4","g8f6","e1g1",
        "f8e7","f1e1","b7b5","a4b3","d7d6","c2c3","e8g8",
    ]),
    ("Apertura Spagnola — Variante Aperta (Berlino)", [
        "e2e4","e7e5","g1f3","b8c6","f1b5","g8f6","e1g1","f6e4","d2d4",
    ]),
    ("Apertura Spagnola — Difesa Marshalliana", [
        "e2e4","e7e5","g1f3","b8c6","f1b5","a7a6","b5a4","g8f6","e1g1",
        "f8e7","f1e1","b7b5","a4b3","e8g8","c2c3","d7d5",
    ]),

    ("Apertura Scozzese", [
        "e2e4","e7e5","g1f3","b8c6","d2d4","e5d4","f3d4",
    ]),
    ("Gambetto Scozzese", [
        "e2e4","e7e5","g1f3","b8c6","d2d4","e5d4","f1c4",
    ]),

    ("Gambetto di Re — Accettato", [
        "e2e4","e7e5","f2f4","e5f4","g1f3","d7d5","e4d5","g8f6",
    ]),
    ("Gambetto di Re — Rifiutato (Difesa Falkbeer)", [
        "e2e4","e7e5","f2f4","d7d5","e4d5","e5e4","d2d3",
    ]),

    ("Apertura dei Quattro Cavalli — Variante Spagnola", [
        "e2e4","e7e5","g1f3","b8c6","b1c3","g8f6","f1b5",
    ]),
    ("Apertura dei Quattro Cavalli — Variante Scozzese", [
        "e2e4","e7e5","g1f3","b8c6","b1c3","g8f6","d2d4",
    ]),

    ("Apertura Ponziani", [
        "e2e4","e7e5","g1f3","b8c6","c2c3","d7d5","d1a4",
    ]),

    # ── DIFESA SICILIANA 1.e4 c5 ─────────────────────────────────────────────

    ("Difesa Siciliana — Variante Najdorf", [
        "e2e4","c7c5","g1f3","d7d6","d2d4","c5d4","f3d4","g8f6",
        "b1c3","a7a6","f1e2","e7e5","d4b3","f8e7",
    ]),
    ("Difesa Siciliana — Variante del Drago", [
        "e2e4","c7c5","g1f3","d7d6","d2d4","c5d4","f3d4","g8f6",
        "b1c3","g7g6","f1e2","f8g7","e1g1","e8g8",
    ]),
    ("Difesa Siciliana — Attacco del Drago Yugoslavo", [
        "e2e4","c7c5","g1f3","d7d6","d2d4","c5d4","f3d4","g8f6",
        "b1c3","g7g6","c1e3","f8g7","f2f3","e8g8","d1d2","b8c6",
    ]),
    ("Difesa Siciliana — Variante Classica", [
        "e2e4","c7c5","g1f3","b8c6","d2d4","c5d4","f3d4","g8f6",
        "b1c3","d7d6","f1e2","e7e6","e1g1","f8e7","d4b3",
    ]),
    ("Difesa Siciliana — Variante Scheveningen", [
        "e2e4","c7c5","g1f3","d7d6","d2d4","c5d4","f3d4","g8f6",
        "b1c3","e7e6","f1e2","a7a6","e1g1",
    ]),
    ("Difesa Siciliana — Variante Kan", [
        "e2e4","c7c5","g1f3","e7e6","d2d4","c5d4","f3d4","a7a6",
        "b1c3","d8c7","f1d3",
    ]),
    ("Difesa Siciliana — Attacco Alapin", [
        "e2e4","c7c5","c2c3","g8f6","e4e5","f6d5","d2d4","c5d4",
        "g1f3","b8c6","c3d4",
    ]),
    ("Difesa Siciliana — Variante Sveshnikov", [
        "e2e4","c7c5","g1f3","b8c6","d2d4","c5d4","f3d4","g8f6",
        "b1c3","e7e5","d4b5","d7d6","c1g5",
    ]),

    # ── DIFESA FRANCESE 1.e4 e6 ──────────────────────────────────────────────

    ("Difesa Francese — Variante d'Avanzata", [
        "e2e4","e7e6","d2d4","d7d5","e4e5","c7c5","c2c3","b8c6",
        "g1f3","d8b6","a2a3",
    ]),
    ("Difesa Francese — Variante Winawer", [
        "e2e4","e7e6","d2d4","d7d5","b1c3","f8b4","e4e5","c7c5",
        "a2a3","b4c3","b2c3","g8e7",
    ]),
    ("Difesa Francese — Variante Tarrasch", [
        "e2e4","e7e6","d2d4","d7d5","b1d2","g8f6","e4e5","f6d7",
        "f1d3","c7c5","c2c3","b8c6","g1e2",
    ]),
    ("Difesa Francese — Variante Classica", [
        "e2e4","e7e6","d2d4","d7d5","b1c3","g8f6","c1g5","f8e7",
        "e4e5","f6d7","g5e7","d8e7","f2f4",
    ]),

    # ── DIFESA CARO-KANN 1.e4 c6 ─────────────────────────────────────────────

    ("Difesa Caro-Kann — Variante Classica", [
        "e2e4","c7c6","d2d4","d7d5","b1c3","d5e4","c3e4","c8f5",
        "e4g3","f5g6","h2h4","h7h6","g1f3","b8d7","h4h5","g6h7",
    ]),
    ("Difesa Caro-Kann — Variante d'Avanzata", [
        "e2e4","c7c6","d2d4","d7d5","e4e5","c8f5","g1f3","e7e6",
        "f1e2","b8d7","e1g1","g8e7",
    ]),
    ("Difesa Caro-Kann — Variante Panov", [
        "e2e4","c7c6","d2d4","d7d5","e4d5","c6d5","c2c4","g8f6",
        "b1c3","e7e6","g1f3","f8e7",
    ]),

    # ── DIFESA PIRC / MODERNA ─────────────────────────────────────────────────

    ("Difesa Pirc — Variante Classica", [
        "e2e4","d7d6","d2d4","g8f6","b1c3","g7g6","g1f3","f8g7",
        "f1e2","e8g8","e1g1","b8c6",
    ]),
    ("Difesa Moderna", [
        "e2e4","g7g6","d2d4","f8g7","b1c3","d7d6","f2f4","b8c6",
        "g1f3","e7e6",
    ]),

    # ── GIOCO DI DONNA 1.d4 d5 ───────────────────────────────────────────────

    ("Gambetto di Donna — Accettato (QGA)", [
        "d2d4","d7d5","c2c4","d5c4","g1f3","g8f6","e2e3","e7e6",
        "f1c4","c7c5","e1g1","a7a6",
    ]),
    ("Gambetto di Donna — Rifiutato, Variante Ortodossa", [
        "d2d4","d7d5","c2c4","e7e6","b1c3","g8f6","c1g5","f8e7",
        "e2e3","e8g8","g1f3","b8d7","d1c2","c7c6","a1d1","d8a5",
    ]),
    ("Gambetto di Donna — Variante Cambridge Springs", [
        "d2d4","d7d5","c2c4","e7e6","b1c3","g8f6","c1g5","b8d7",
        "e2e3","c7c6","g1f3","d8a5",
    ]),
    ("Gambetto di Donna — Variante Tartakower", [
        "d2d4","d7d5","c2c4","e7e6","b1c3","g8f6","c1g5","f8e7",
        "e2e3","e8g8","g1f3","h7h6","g5h4","b7b6",
    ]),

    ("Difesa Slava", [
        "d2d4","d7d5","c2c4","c7c6","g1f3","g8f6","b1c3","d5c4",
        "a2a4","c8f5","e2e3","e7e6","f1c4",
    ]),
    ("Difesa Semi-Slava — Variante Merano", [
        "d2d4","d7d5","c2c4","c7c6","b1c3","g8f6","g1f3","e7e6",
        "e2e3","b8d7","f1d3","d5c4","d3c4","b7b5","c4d3",
    ]),
    ("Difesa Semi-Slava — Gambetto Botvinnik", [
        "d2d4","d7d5","c2c4","c7c6","b1c3","g8f6","g1f3","e7e6",
        "c1g5","d5c4","e2e4","b7b5","e4e5","h7h6","g5h4","g7g5",
    ]),

    # ── DIFESE INDIANE 1.d4 Nf6 ──────────────────────────────────────────────

    ("Difesa Indiana di Re — Variante Classica", [
        "d2d4","g8f6","c2c4","g7g6","b1c3","f8g7","e2e4","d7d6",
        "g1f3","e8g8","f1e2","e7e5","e1g1","b8c6","d4d5","c6e7",
    ]),
    ("Difesa Indiana di Re — Variante Sämisch", [
        "d2d4","g8f6","c2c4","g7g6","b1c3","f8g7","e2e4","d7d6",
        "f2f3","e8g8","c1e3","e7e5","d4d5","b8d7",
    ]),
    ("Difesa Indiana di Re — Attacco dei Quattro Pedoni", [
        "d2d4","g8f6","c2c4","g7g6","b1c3","f8g7","e2e4","d7d6",
        "f2f4","e8g8","g1f3","c7c5","d4d5","b7b5",
    ]),

    ("Difesa Nimzo-Indiana — Variante Classica", [
        "d2d4","g8f6","c2c4","e7e6","b1c3","f8b4","d1c2","d7d5",
        "a2a3","b4c3","c2c3","b8c6","g1f3","e8g8",
    ]),
    ("Difesa Nimzo-Indiana — Variante Rubinstein", [
        "d2d4","g8f6","c2c4","e7e6","b1c3","f8b4","e2e3","e8g8",
        "f1d3","d7d5","g1f3","c7c5","e1g1","b8c6","a2a3","b4c3",
    ]),
    ("Difesa Nimzo-Indiana — Variante Sämisch", [
        "d2d4","g8f6","c2c4","e7e6","b1c3","f8b4","a2a3","b4c3",
        "b2c3","e8g8","f2f3","d7d5","c4d5","e6d5",
    ]),

    ("Difesa Grünfeld — Variante di Scambio", [
        "d2d4","g8f6","c2c4","g7g6","b1c3","d7d5","c4d5","f6d5",
        "e2e4","d5c3","b2c3","f8g7","f1c4","c7c5","g1e2","b8c6",
    ]),
    ("Difesa Grünfeld — Variante Russa", [
        "d2d4","g8f6","c2c4","g7g6","b1c3","d7d5","g1f3","f8g7",
        "d1b3","d5c4","b3c4","e8g8","e2e4","c8g4","c1e3",
    ]),

    ("Difesa Indiana di Donna", [
        "d2d4","g8f6","c2c4","e7e6","g1f3","b7b6","g2g3","c8b7",
        "f1g2","f8e7","e1g1","e8g8","b1c3","g8h8",
    ]),

    ("Difesa Olandese — Variante Stonewall", [
        "d2d4","f7f5","g2g3","g8f6","f1g2","e7e6","g1f3","d7d5",
        "e1g1","f8d6","c2c4","c7c6","b2b3","d8e7",
    ]),
    ("Difesa Olandese — Variante Classica", [
        "d2d4","f7f5","c2c4","g8f6","g2g3","e7e6","f1g2","f8e7",
        "g1f3","e8g8","e1g1","d7d6","b1c3","d8e8",
    ]),

    # ── GAMBETTO DI BUDAPEST ─────────────────────────────────────────────────

    ("Gambetto di Budapest", [
        "d2d4","g8f6","c2c4","e7e5","d4e5","f6g4","g1f3","f8c5",
        "e2e3","b8c6","f1e2","d8e7",
    ]),

    # ── SISTEMA LONDINESE ─────────────────────────────────────────────────────

    ("Sistema Londinese", [
        "d2d4","d7d5","g1f3","g8f6","c1f4","e7e6","e2e3","c7c5",
        "c2c3","b8c6","b1d2","f8d6","f4d6","d8d6","f1d3","e8g8",
    ]),
    ("Sistema Londinese — vs KID", [
        "d2d4","g8f6","g1f3","g7g6","c1f4","f8g7","e2e3","e8g8",
        "h2h3","d7d6","f1e2","b8d7","e1g1",
    ]),

    # ── APERTURA INGLESE ─────────────────────────────────────────────────────

    ("Apertura Inglese — Variante Simmetrica", [
        "c2c4","c7c5","b1c3","b8c6","g2g3","g7g6","f1g2","f8g7",
        "g1f3","e7e6","e1g1","g8e7","d2d3","e8g8",
    ]),
    ("Apertura Inglese — Difesa Indiana", [
        "c2c4","g8f6","b1c3","e7e6","g1f3","f8b4","g2g3","e8g8",
        "f1g2","d7d5","e1g1","c7c6",
    ]),
    ("Apertura Inglese — Hedgehog", [
        "c2c4","c7c5","g1f3","g8f6","b1c3","e7e6","g2g3","b7b6",
        "f1g2","c8b7","e1g1","a7a6","d2d4","c5d4","d1d4","d8c7",
    ]),

    # ── APERTURA RETI ─────────────────────────────────────────────────────────

    ("Apertura Reti", [
        "g1f3","d7d5","c2c4","d5d4","b2b4","c7c6","g2g3","g8f6",
        "f1g2","g7g6","e1g1","f8g7",
    ]),
    ("Apertura Reti — Variante King's Indian", [
        "g1f3","g8f6","c2c4","g7g6","g2g3","f8g7","f1g2","e8g8",
        "e1g1","d7d6","d2d3","e7e5","b1c3",
    ]),

    # ── APERTURA CATALANA ─────────────────────────────────────────────────────

    ("Apertura Catalana — Variante Aperta", [
        "d2d4","g8f6","c2c4","e7e6","g2g3","d7d5","f1g2","d5c4",
        "g1f3","a7a6","e1g1","b7b5","b1d2","c8b7","d1c2","b8d7",
    ]),
    ("Apertura Catalana — Variante Chiusa", [
        "d2d4","g8f6","c2c4","e7e6","g2g3","d7d5","f1g2","f8e7",
        "g1f3","e8g8","e1g1","d5c4","d1c2","a7a6","c2c4",
    ]),

    # ── TORRE / COLLE ─────────────────────────────────────────────────────────

    ("Sistema Colle", [
        "d2d4","d7d5","g1f3","g8f6","e2e3","e7e6","f1d3","c7c5",
        "c2c3","b8c6","b1d2","f8d6","e1g1","e8g8","d1e2","d8c7",
    ]),
    ("Apertura Torre", [
        "d2d4","g8f6","g1f3","e7e6","c1g5","c7c5","e2e3","b7b6",
        "f1d3","c8b7","b1d2","d7d5","c2c3","b8d7",
    ]),
]


# ── Indicizzazione ────────────────────────────────────────────────────────────

def _moves_to_key(moves):
    """Converte una lista di mosse long-algebraic in una tupla di coordinate."""
    s = init_state()
    key = []
    turn = 'white'
    for mv_str in moves:
        try:
            src = algebraic_to_coord(mv_str[:2])
            dst = algebraic_to_coord(mv_str[2:4])
            promo = mv_str[4].upper() if len(mv_str) == 5 else None
            mv = (src, dst)
            key.append(mv)
            s = apply_move(s, mv, promo)
            turn = 'white' if turn == 'black' else 'black'
        except Exception:
            break
    return tuple(key)

# Costruisce il libro: history_tuple → lista di (next_move, nome_apertura)
def _build_book():
    book = {}
    for name, moves in OPENINGS_RAW:
        key_moves = _moves_to_key(moves)
        # Registra ogni prefisso → continuazione
        for i in range(len(key_moves) - 1):
            prefix = key_moves[:i]
            next_mv = key_moves[i]
            if prefix not in book:
                book[prefix] = []
            book[prefix].append((next_mv, name))
    return book

BOOK = _build_book()


# ── Interfaccia pubblica ──────────────────────────────────────────────────────

def book_move(history):
    """
    Dato lo storico delle mosse (lista di tuple ((r1,c1),(r2,c2))),
    restituisce (mossa, nome_apertura) se esiste una continuazione nel libro,
    altrimenti (None, None).

    Se ci sono più continuazioni valide, ne sceglie una a caso.
    """
    key = tuple(history)
    candidates = BOOK.get(key)
    if not candidates:
        return None, None
    mv, name = random.choice(candidates)
    return mv, name
