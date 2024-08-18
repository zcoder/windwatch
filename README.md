
# WindWatch

**WindWatch** is a Python-based utility designed to monitor and manage active windows on your Linux system. The tool helps you set time limits for specific windows, automatically closing them if the time limit is exceeded, thereby helping to manage focus and productivity.

## Getting Started

### 1. Building the Package

First, you need to build the Debian package for WindWatch. This can be done using the provided `build.sh` script.

1. Ensure that the `build.sh` script is executable:

    ```bash
    chmod +x build.sh
    ```

2. Run the build script:

    ```bash
    ./build.sh
    ```

   This will create a Debian package named `windwatch_1.0-1.deb`.

### 2. Installing the Package

Once the package is built, you can install it using `dpkg`:

```bash
sudo dpkg -i .build/windwatch_1.0-1.deb
```

If there are any missing dependencies, you can resolve them with:

```bash
sudo apt install -f
```

### 3. Remove the Package

For remove package

```bash
sudo apt remove windwatch
```


For complete remove package with config files

```bash
sudo apt purge windwatch
```

### 4. Configuration

WindWatch uses a configuration file in JSON format. The default configuration file is located at `/etc/windwatch/windwatch.json`.

`*** Config WINDOWS_SETTINGS part will reload every RECORDS_TTL_CHECK_INTERVAL. ***`

Here is an example configuration:

```json
{
    "DISPLAY": null,
    "USER": 1000,
    "CHECK_INTERVAL": 1,
    "DEBUG": 1,
    "REAL_TERMINATE": 1,
    "RECORDS_TTL": 86400,
    "RECORDS_TTL_CHECK_INTERVAL": 10,
    "LOG_FILE": "/var/log/windwatch/windwatch_apps.log",
    "WINDOWS_SETTINGS": {
        "telegram-desktop": -1,
        "Банки, деньги, два.+": 300,
        "MarketTwits –": 300,
        ".*YouTube.*Yandex.*Browser.*": 300,
        "firefox": -1,
        "yandex-browser": -1
    }
}
```

- **DISPLAY**: The X display to use. Default is `:0`.
- **USER**: The user ID or username to run the service under.
- **CHECK_INTERVAL**: Interval in seconds to check for active windows.
- **DEBUG**: Set to `1` for debug mode.
- **REAL_TERMINATE**: Set to `1` for activate terminate feature.
- **RECORDS_TTL**: Time-to-live for records in seconds.
- **LOG_FILE**: Path to the log file.
- **WINDOWS_SETTINGS**: A dictionary of window titles or patterns and their corresponding time limits in seconds.

### 5. Running the Service (will run automatically after install package)

Once installed and configured, you can start the WindWatch service using `systemctl`.

1. Start the service:

    ```bash
    sudo systemctl start windwatch.service
    ```

2. Enable the service to start on boot:

    ```bash
    sudo systemctl enable windwatch.service
    ```

3. Check the status of the service:

    ```bash
    sudo systemctl status windwatch.service
    ```

### 6. Logs

By default, logs are stored in `/var/log/windwatch/windwatch_apps.log`. You can view the logs with:

```bash
cat /var/log/windwatch/windwatch_apps.log
```

Or follow the logs in real-time:

```bash
tail -F /var/log/windwatch/windwatch_apps.log
```

### 7. Service Logs

By default, service logs are stored in `/var/log/windwatch/windwatch_service.log`. You can view the logs with:

```bash
cat /var/log/windwatch/windwatch_service.log
```

Or follow the service logs in real-time:

```bash
tail -F /var/log/windwatch/windwatch_service.log
```

## Development

If you wish to contribute to the development of WindWatch, or just want to modify it for your own use, follow these steps:

### 1. Installing Dependencies

WindWatch uses Python 3 and requires a few dependencies. If you have `Poetry` installed, you can set up the development environment as follows:

1. Install Poetry if you haven't already:

    ```bash
    curl -sSL https://install.python-poetry.org | python3 -
    ```

2. Install the dependencies:

    ```bash
    poetry install
    ```

### 2. Running WindWatch in Development Mode

You can run WindWatch directly from the source for development:

```bash
poetry run python windwatch.py --config /path/to/your/windwatch.json
```

### 3. Testing

You can add tests using `pytest`. To run tests:

```bash
poetry run pytest
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

WindWatch is a simple yet powerful tool designed to help you maintain focus by automatically closing distracting windows after a set period of time.
