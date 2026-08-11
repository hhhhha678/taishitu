from .dashboard_loader import repository


def main() -> None:
    payload = repository.get_dashboard()
    print(f"dashboard loaded: {payload['date_range']['from']} -> {payload['date_range']['to']}")


if __name__ == "__main__":
    main()
