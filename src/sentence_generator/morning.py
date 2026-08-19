"""This module contains functionality for sending morning greeting messages.

It includes the scheduling of morning greetings using a specified time range and a Telegram client.
The module leverages the APScheduler for job scheduling and allows for dynamic configuration of
greeting times, enabling automated daily greetings to be sent at random times within the defined
interval.
"""

from src.sentence_generator.sentence_generator import (
    CustomGeneratedText,
    SentenceGenerator,
    Token,
)
from src.utils.random import low_random

amor = Token("amor")
mi_amor = Token("mi amor")

amorcita = Token("amorcita")
mi_amorcita = Token("mi amorcita")

amorcito = Token("amorcito")
mi_amorcito = Token("mi amorcito")

amooor = Token(CustomGeneratedText(lambda: "am" + "o" * low_random(1, 10) + "r"))
mi_amooor = Token(CustomGeneratedText(lambda: "mi am" + "o" * low_random(1, 10) + "r"))

amorcitaaa = Token(CustomGeneratedText(lambda: "amorcit" + "a" * low_random(1, 10)))
mi_amorcitaaa = Token(CustomGeneratedText(lambda: "mi amorcit" + "a" * low_random(1, 10)))

amorcitooo = Token(CustomGeneratedText(lambda: "amorcit" + "o" * low_random(1, 10)))
mi_amorcitooo = Token(CustomGeneratedText(lambda: "mi amorcit" + "o" * low_random(1, 10)))

mailob = Token("mailob")
my_love = Token("my love")

preciosura_tropical = Token("preciosura tropical")


general_right_part: list[Token] = [
    amooor,
    mi_amooor,
    amorcitaaa,
    mi_amorcitaaa,
    amorcitooo,
    mi_amorcitooo,
    mailob,
    my_love,
    preciosura_tropical,
]


hola = Token(CustomGeneratedText(lambda: "Hol" + "a" * low_random(1, 10))).add_next_tokens(
    *general_right_part
)
buenos_dias = Token("Buenos días").add_next_tokens(
    *general_right_part,
    Token("señorita"),
    Token("princesita"),
)
wenas = (
    Token("Wenas")
    .add_next_tokens(
        *[
            Token(
                token.value,
                pick_next=lambda tokens: tokens[low_random(0, len(tokens) - 1)],
            ).add_next_tokens(
                Token(""),
                Token(CustomGeneratedText(lambda: "wen" + "a" * low_random(1, 5) + "s")),
            )
            for token in general_right_part
        ]
    )
    .add_next_token(preciosura_tropical)
)
guenas = Token("Güenas").add_next_tokens(
    *general_right_part,
)
jelou = Token("Jelou").add_next_tokens(
    *general_right_part,
)
jeloucito = Token("Jeloucito").add_next_tokens(
    mi_amorcitooo,
    mailob,
    my_love,
    preciosura_tropical,
)
gusmornin = Token("Gusmornin").add_next_tokens(
    *general_right_part,
)
good_morning = Token("Good morning").add_next_tokens(
    *general_right_part,
)
god_morgon = Token("God morgon").add_next_tokens(*general_right_part, Token("prinsessa"))
bonjour = Token("Bonjour").add_next_tokens(
    Token("mademoiselle"),
    Token("princesse"),
)
buongiorno = Token("Buongiorno").add_next_tokens(
    Token("principessa"),
    Token("signorina"),
)


sentences = SentenceGenerator(
    [
        hola,
        buenos_dias,
        wenas,
        guenas,
        jelou,
        gusmornin,
        good_morning,
        god_morgon,
        bonjour,
        buongiorno,
    ]
)


def get_morning_greeting() -> str:
    """Get a random good morning message along with emojis.

    This function retrieves a random good morning greeting and appends a selection of random emojis
    to enhance the message. It ensures that at least one emoji is included in the final output.

    Returns:
        str: A string containing a random good morning message followed by a selection of emojis.
    """
    greeting: str = sentences.eval()

    emoji1: list[str] = [
        "",
        "\U0001f44b",  # 👋
        "\U0000270c",  # Hand with 2 raised fingers
    ]
    emoji2: list[str] = [
        "",
        "\U0001f61b",  # 😛
        "\U0001f61d",  # 😝
        "\U0001f92a",  # 🤪
        "\U0001f60b",  # 😋
    ]
    emoji3: list[str] = [
        "",
        "\U0001f643",  # 🙃
        "\U0001f601",  # 😁
        "\U0001f604",  # 😄
        "\U0001f603",  # 😃
    ]
    emoji4: list[str] = [
        "",
        "\U0001f917",  # 🤗
        "\U0001f61a",  # 😚
        "\U0001f60a",  # 😊
        "\U0000263a",  # ☺ smiling face
        "\U0001f92d",  # 🤭
    ]
    emoji5: list[str] = [
        "",
        "\U0001f970",  # 🥰
        "\U0001f618",  # 😘
    ]
    emoji6: list[str] = [
        "",
        "\U0001faf6",  # 🫶
        "\U00002764",  # ❤ red heart
    ]

    def get_emoji(emojis: list[str], p: float) -> str:
        """Gets a random emoji from a list based on a specified probability.

        This function selects an emoji from the provided list using a random selection method that
        takes into account the specified probability. The probability influences the likelihood of
        each emoji being chosen, allowing for customized emoji selection.

        Args:
            emojis (list[str]): The list of emojis to choose from.
            p (float): The probability factor that influences the selection of the emoji. Refer to
                `utils.random.low_random` documentation.

        Returns:
            str: The randomly selected emoji from the list.
        """
        return emojis[low_random(1, len(emojis), p) - 1]

    def get_all_emojis() -> str:
        """Get a random text made of emojis.

        This function generates a string composed of randomly selected emojis from predefined lists.
        It combines multiple emojis to create a fun and varied emoji text output.

        Returns:
            str: The random text made of emojis.
        """
        return (
            get_emoji(emoji1, 3.5)
            + get_emoji(emoji2, 5)
            + get_emoji(emoji3, 4)
            + get_emoji(emoji4, 3)
            + get_emoji(emoji5, 1.3)
            + get_emoji(emoji6, 2)
        )

    emojis: str = ""
    while not emojis:
        emojis = get_all_emojis()

    return f"{greeting} {emojis}"
