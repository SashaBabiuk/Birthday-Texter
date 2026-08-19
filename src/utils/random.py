"""This module contains utility functions for generating random values.

It includes the `low_random` function, which generates a low-biased random integer within a
specified range, and the `random_time` function, which generates a random time duration between two
specified time intervals. These functions can be used to introduce variability and randomness in
applications requiring random number generation.
"""

import random
from datetime import timedelta


def low_random(a: int, b: int, p: float = 2) -> int:
    """Generates a low-biased random integer between two specified values.

    This function skews the randomness towards the lower end, upper end or uniform distribution of
    the specified range.

    The generated integer is calculated using a power function to adjust the distribution,
    making it more likely to return values closer to the lower bound, upper bound or uniform
    distribution according to the parameter p.

    Args:
        a (int): The lower bound of the random integer range.
        b (int): The upper bound of the random integer range.
        p (float, optional): The power parameter that influences the skewness of the distribution.
            Always greater than 0.
            If p = 1 then this is the uniform distribution.
            If p > 1 makes it more likely to return values closer to the lower bound.
            If p < 1 makes it more likely to return values closer to the upper bound.
            Defaults to 2.

    Returns:
        int: A low-biased random integer within the specified range [a, b].
    """
    return a + int((b - a + 1) * (random.random() ** p))


def random_time(start: timedelta, end: timedelta) -> timedelta:
    """Generates a random time duration between two specified time intervals.

    This function returns a random timedelta that falls within the range defined by the start and
    end parameters.

    The generated random time is inclusive on both the start and end time, allowing for variability
    in time calculations.

    Args:
        start (timedelta): The lower bound of the time interval.
        end (timedelta): The upper bound of the time interval.

    Returns:
        timedelta: A random timedelta representing a duration within the specified range.
    """
    return timedelta(seconds=random.randint(int(start.total_seconds()), int(end.total_seconds())))
