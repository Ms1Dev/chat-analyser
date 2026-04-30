
makemigrations:
    docker compose run --rm web python manage.py makemigrations


migrate:
    docker compose run --rm web python manage.py migrate


uv *args:
	docker compose run --rm web uv {{ args }}

manage *args:
	docker compose run --rm web uv run manage.py {{ args }}

