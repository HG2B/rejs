test:
    #!/bin/bash
    # Run redis-server
    if [ -z "$(docker ps -q -f name=redis)" ]; then
        docker run -d \
            -p 6379:6379 \
            --name redis \
            redis
    fi
    # Check if redis is running and it's ready
    docker ps | grep redis
    # Wait for redis to be ready
    while ! docker exec redis redis-cli ping | grep PONG; do sleep 1; done

    # Run tests in rejs directories
    cd rejs
    uv run pytest

stop-redis:
    #!/bin/bash
    if [ -n "$(docker ps -q -f name=redis)" ]; then
        docker container stop redis
        docker container rm redis
    fi
