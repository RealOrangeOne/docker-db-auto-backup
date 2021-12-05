#!/usr/bin/env python3

import docker


def main() -> None:
    docker_client = docker.from_env()
    print("Found some containers:", len(docker_client.containers.list()))


if __name__ == "__main__":
    main()
