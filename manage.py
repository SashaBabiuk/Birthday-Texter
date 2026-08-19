"""This module serves as the main entry point for the Telegram bot application.

It handles the initialization of the command-line interface, sets up argument parsing, and invokes
the appropriate command functions based on user input. The module integrates with various worker
functions to perform tasks such as sending messages and managing media, while providing a structured
way to interact with the application through command-line commands.
"""

import inspect
import subprocess
import sys
from argparse import (
    ArgumentDefaultsHelpFormatter,
    ArgumentParser,
    Namespace,
    _SubParsersAction,
)


def deploy(args: Namespace):
    """Deploys the Docker container for the Telegram Auto Texter application.

    This function checks for any running instances of the Telegram Auto Texter container and
    optionally copies the register file from the container to the local directory. It then builds
    a new Docker image with the specified name and tag, and runs the container in detached mode.

    Args:
        args (argparse.Namespace): The command-line arguments containing options for deployment,
            including whether to copy the register and the name and tag for the Docker image.

    Raises:
        subprocess.CalledProcessError: If any of the subprocess commands fail during execution.
    """
    proc = subprocess.Popen(
        [
            "docker",
            "ps",
            "-q",
            "-f",
            "ancestor=telegram-auto-texter",
            "-f",
            "status=running",
        ],
        stdout=subprocess.PIPE,
        shell=True,
    )
    out, err = proc.communicate()
    cid = out.decode("utf-8").strip()
    if cid != "":
        if args.register:
            subprocess.run(
                [
                    "docker",
                    "container",
                    "cp",
                    f"{cid}:/telegram-auto-texter/src/data/register.yaml",
                    "src/",
                ]
            )
        subprocess.run(["docker", "stop", cid])

    subprocess.run(["docker", "build", ".", "-t" f"{args.name}:{args.tag}"])
    subprocess.run(["docker", "run", "-d", f"{args.name}:{args.tag}"])


def deploy_cli(subparsers: _SubParsersAction):
    """Sets up the command-line interface for the deploy command.

    This function configures the argument parser for the deploy command, allowing users to specify
    deployment settings such as the image name and tag. It also includes an option to disable
    registration during deployment.

    Args:
        subparsers (argparse._SubParsersAction): The subparsers object used to add the deploy
            command to the CLI.
    """
    parser: ArgumentParser = subparsers.add_parser(
        "deploy", help="Settings for deploying the project"
    )
    parser.add_argument("--name", "-n", default="telegram-auto-texter", help="")
    parser.add_argument("--tag", "-t", default="latest", help="")
    parser.add_argument("--no-register", dest="register", action="store_false", help="")


def parse_args() -> Namespace:
    """Parses command-line arguments for the application.

    This function sets up an argument parser with subcommands based on functions that end with
    '_cli' in the current module. It returns the parsed arguments, allowing the application to
    handle different commands and options provided by the user.

    Returns:
        argparse.Namespace: The parsed command-line arguments.

    Raises:
        SystemExit: If the command-line arguments are invalid or if a required command is not
            provided.
    """
    parser = ArgumentParser("qwerty", formatter_class=ArgumentDefaultsHelpFormatter)

    subparsers = parser.add_subparsers(dest="command")
    for name, obj in inspect.getmembers(sys.modules[__name__]):
        if inspect.isfunction(obj) and name.endswith("_cli"):
            obj(subparsers)

    return parser.parse_args()


def main():
    """Main entry point for the application.

    This function parses the command-line arguments and invokes the corresponding command function
    based on the user's input. It serves as the starting point for executing the application's
    functionality.

    Raises:
        AttributeError: If the command specified in the arguments does not correspond to a valid
            function.
        SystemExit: If there are issues with parsing the command-line arguments.
    """
    args = parse_args()
    getattr(sys.modules[__name__], args.command)(args)


if __name__ == "__main__":
    main()
