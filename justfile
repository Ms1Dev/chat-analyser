
makemigrations:
    docker compose run --rm web python manage.py makemigrations


migrate:
    docker compose run --rm web python manage.py migrate


uv arg:
	docker compose run --rm web uv {{ arg }}

manage arg:
	docker compose run --rm web uv run manage.py {{ arg }}

