import docker


def main() -> None:
    docker_client = docker.from_env()
    docker_client.containers.list()


if __name__ == "__main__":
    main()
