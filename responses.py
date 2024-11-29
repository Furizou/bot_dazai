from random import choice, randint

def get_response(user_input: str) -> str:
    lowered: str = user_input.lower()
    
    if lowered == '':
        return 'apaan'
    elif 'hello' in lowered:
        return 'HAI COK'
    elif 'judol' in lowered:
        return f'Selamat kamu dapat nomor: {randint(1,6)}'
    else:
        return choice(['Ngomong apa sih nyet',
                       'Sorry gapaham',
                       'Mana kutau kau mau apa',])

    # raise NotImplementedError('Code is missing...')