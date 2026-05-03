
makemigrations:
    docker compose run --rm web uv run manage.py makemigrations


migrate:
    docker compose run --rm web uv run manage.py migrate


uv *args:
	docker compose run --rm web uv {{ args }}

manage *args:
	docker compose run --rm web uv run manage.py {{ args }}

test:
    docker compose run --rm web uv run manage.py test
