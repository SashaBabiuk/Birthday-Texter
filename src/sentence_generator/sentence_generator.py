"""This module provides classes for generating custom text and sentences using tokens.

It includes the `CustomGeneratedText` class for creating text from a generator function, the `Token`
class for representing individual tokens in a sentence, and the `SentenceGenerator` class for
assembling sentences from a list of tokens. These components work together to allow for flexible and
dynamic sentence generation based on defined token relationships and selection algorithms.
"""

from collections.abc import Callable
from random import choice
from typing import Union


class CustomGeneratedText:
    """Represents a custom generated text.

    This class encapsulates a text generator function, allowing for the creation of dynamic text
    based on the logic defined within the generator. It provides a simple interface to retrieve
    the generated text as a string.
    """

    def __init__(self, generator: Callable[[], str]):
        """Creates a custom generated text class.

        This constructor initializes the `CustomGeneratedText` instance with a specified text
        generator function.

        Args:
            generator (Callable[[], str]): The text generator function that produces a string when
                called.
        """
        self.generator = generator

    def __repr__(self) -> str:
        """Return the generated text as a string.

        This method calls the generator function and returns the resulting string.

        Returns:
            str: The generated text from the generator function.
        """
        return str(self.generator())


class Token:
    """Represents a token of a sentence.

    This class encapsulates a single unit of a sentence, which can be a word or a generated text.
    It manages the value of the token and the possible next tokens that can follow it, allowing
    for the construction of dynamic and flexible sentence structures.
    """

    def __init__(
        self,
        value: str | CustomGeneratedText,
        pick_next: Callable[[list["Token"]], "Token"] = choice,
    ):
        """Creates a token of a sentence.

        This constructor initializes the `Token` instance with a specified value and a method for
        selecting the next token in the sequence. It allows for the creation of complex sentence
        structures by linking multiple tokens together.

        Args:
            value (str | CustomGeneratedText): The value of the token, which can be a string or a
                custom generated text.
            pick_next (Callable[[list[Token]], Token], optional): Algorithm to pick the next token
                after this one. Defaults to random.choice.
        """
        super().__init__()
        self.value = value
        self.pick_next = pick_next
        self.next_tokens: list[Token] = []

    def eval(self) -> str:
        """Evaluate this token.

        This method processes the token's value and appends the value of the next token, if
        available. It constructs a string representation of the token and its subsequent tokens,
        forming part of a complete sentence.

        Returns:
            str: The evaluated string representation of the token and its next tokens.
        """
        left = str(self.value)
        next_token = self.get_next_token()
        right = "" if next_token is None else next_token.eval()
        return f"{left}{' ' if left != '' and right != '' else ''}{right}"

    def get_next_token(self) -> Union["Token", None]:
        """Gets the next token, if any.

        This method retrieves the next token in the sequence based on the defined selection
        algorithm. If no next tokens are available, it returns None.

        Returns:
            Union[Token, None]: The next token, if available; otherwise, None.
        """
        return None if len(self.next_tokens) == 0 else self.pick_next(self.next_tokens)

    def add_next_token(self, next_token: "Token") -> "Token":
        """Adds a possible next token to this one.

        This method allows for the addition of a single next token to the current token, enabling
        the construction of a sequence of tokens.

        Args:
            next_token (Token): The possible next token to be added.

        Returns:
            Token: Returns itself, allowing for method chaining in a builder design pattern.
        """
        self.next_tokens.append(next_token)
        return self

    def add_next_tokens(self, *next_tokens: "Token") -> "Token":
        """Adds multiple possible next tokens to this one.

        This method allows for the addition of multiple next tokens to the current token,
        facilitating the creation of more complex token sequences.

        Args:
            _ (Token): Possible next tokens to be added.

        Returns:
            Token: Returns itself, allowing for method chaining in a builder design pattern.
        """
        self.next_tokens.extend(next_tokens)
        return self


class SentenceGenerator:
    """Represents a sentence generator algorithm class.

    This class is responsible for generating sentences by evaluating a set of initial tokens.
    It utilizes a selection algorithm to determine the root token and constructs sentences
    dynamically based on the relationships between tokens, allowing for varied and creative sentence
    generation.
    """

    def __init__(
        self,
        initial_tokens: list[Token],
        pick_root: Callable[[list["Token"]], "Token"] = choice,
    ):
        """Creates a sentence generator algorithm class.

        This constructor initializes the `SentenceGenerator` with a list of initial tokens and a
        method for selecting the root token of the sentence. It sets up the necessary components for
        generating sentences based on the provided tokens.

        Args:
            initial_tokens (list[Token]): List of all possible initial tokens for sentence
                generation.
            pick_root (Callable[[list[Token]], Token], optional): Algorithm to pick the root token
                of the sentence. Defaults to random.choice.
        """
        self.initial_tokens = initial_tokens
        self.pick_root = pick_root

    def eval(self) -> str:
        """Evaluate this sentence generator.

        This method generates a complete sentence by selecting a root token and evaluating it along
        with its subsequent tokens. It constructs the final string representation of the generated
        sentence.

        Returns:
            str: The generated sentence based on the initial tokens and their relationships.
        """
        return "" if len(self.initial_tokens) == 0 else self.pick_root(self.initial_tokens).eval()
