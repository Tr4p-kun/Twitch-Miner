# Twitch Miner Bot

This bot automates watching Twitch streams to farm channel points and claim drops. It intelligently selects streams for a specified game, focusing on those with drops enabled and a minimum viewer count, and cycles through them at random intervals.

## Features

- **Automated Stream Hopping**: Periodically finds new streams for a target game to watch.
- **Drops-Focused**: Prioritizes streams that have Twitch Drops enabled.
- **Configurable Filters**: Set a minimum viewer count to avoid empty streams.
- **Randomized Watch Times**: Watches each stream for a random duration to mimic human behavior.
- **Automatic Token Refresh**: Handles the renewal of Twitch API access tokens automatically.
- **Easy Setup**: Includes a script to guide you through obtaining the necessary authentication tokens.
- **Environment-based Configuration**: All settings are managed in a simple `.env` file.

## Setup and Installation

### 1. Prerequisites

- Python 3.x

### 2. Clone the Repository

```bash
git clone https://github.com/Tr4p-kun/Twitch-Miner-Bot.git
cd Twitch-Miner-Bot
```

### 3. Install Dependencies

Install the required Python packages using pip:

```bash
pip install -r requirements.txt
```

### 4. Configure the Bot

You'll need to create a `.env` file to store your credentials and settings.

1.  Make a copy of the example file:
    ```bash
    cp .env.example .env
    ```
2.  Open the new `.env` file and fill in your Twitch Application details:
    - **Create a Twitch Application**:
        1. Go to the [Twitch Developer Console](https://dev.twitch.tv/console/apps) and log in.
        2. Click **"Register Your Application"**.
        3. Give it a name (e.g., "My Miner Bot"), set the **OAuth Redirect URL** to `http://localhost:3000`, and choose a category like "Chat Bot".
        4. Click **"Create"**.
    - **Update `.env`**:
        1. On your application's page, copy the **Client ID** and paste it as the value for `CLIENT_ID` in your `.env` file.
        2. Click **"New Secret"**, copy the new **Client Secret**, and paste it as the value for `CLIENT_SECRET`.
        3. Enter your Twitch `USERNAME`.
        4. Adjust other miner settings like `GAME_ID` and `VIEWER_THRESHOLD` as desired. See the [Configuration](#configuration) section for details.

## Usage

Running the bot is a two-step process. You only need to run the first step once to get your initial token.

### Step 1: Obtain Your Refresh Token

This script exchanges a one-time authorization code for a long-lived refresh token that the miner will use.

1.  **Get an Authorization Code**:
    - Construct the following URL, replacing `YOUR_CLIENT_ID` with the actual **Client ID** from your `.env` file:
      ```
      https://id.twitch.tv/oauth2/authorize?client_id=YOUR_CLIENT_ID&redirect_uri=http://localhost:3000&response_type=code&scope=user:read:email+user:read:follows
      ```
    - Open the completed URL in your web browser.
    - Log in to your Twitch account and authorize the application.
    - You will be redirected to a blank page. The URL in your address bar will look like this: `http://localhost:3000/?code=SOME_LONG_CODE&scope=...`
    - Copy the `code` value from the URL. This is your Authorization Code.

2.  **Run the Setup Script**:
    - Execute the `Run_Me_First.py` script:
      ```bash
      python Run_Me_First.py
      ```
    - When prompted, paste the Authorization Code you just copied and press Enter.
    - The script will automatically obtain a `TWITCH_REFRESH_TOKEN` and save it to your `.env` file.

### Step 2: Start the Miner

Once your `.env` file contains the `TWITCH_REFRESH_TOKEN`, you can start the miner.

```bash
python miner.py
```

The bot will start. It will give you an option to interactively search for a new game or proceed with the `GAME_ID` from your `.env` file. It will then begin searching for streams and cycling through them.

```
🚀  Miner started
✅  Token OK

🎮  Change game? (yes/no): no
  Starting in 3 s …
🎲  streamer123  (pool: 15)
[START] streamer123
  ⏳  45 min …
  ⏳  44 min left
...
[END] streamer123
✅  Switch  (live)  – 30 s
```

## Configuration

All configuration is handled via the `.env` file.

| Variable              | Description                                                                                                                              |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `CLIENT_ID`           | Your Twitch application's Client ID.                                                                                                     |
| `CLIENT_SECRET`       | Your Twitch application's Client Secret.                                                                                                 |
| `AUTH_CODE`           | A temporary code used by `Run_Me_First.py`. The script will save the code you provide.                                                     |
| `TWITCH_REFRESH_TOKEN`| Automatically generated and saved by `Run_Me_First.py`. The miner uses this to stay logged in.                                             |
| `USERNAME`            | The Twitch username of the account you want to use for mining.                                                                           |
| `GAME_ID`             | The numerical ID of the game to watch streams for (e.g., `516575` for Valorant).                                                          |
| `DROPS_ONLY_MODE`     | If `True`, only watches streams with the "DropsEnabled" tag. If `False`, watches any stream for the game.                                  |
| `MINING_DURATION_MIN` | The minimum number of minutes to watch a single stream before switching.                                                                   |
| `MINING_DURATION_MAX` | The maximum number of minutes to watch a single stream before switching.                                                                   |
| `VIEWER_THRESHOLD`    | The minimum number of viewers a stream must have to be considered for mining.                                                              |
| `CHECK_INTERVAL`      | How many seconds to wait before checking for new available streams if none are found.                                                      |
| `DEBUG`               | If `True`, enables verbose logging, including API requests and other internal events.                                                      |
