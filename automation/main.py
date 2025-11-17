#!/usr/bin/env python3
"""
Main entry point for Joseph Carlson Show Stock Tracker automation.
Runs the Crew.ai workflow to update stock data.
"""

import os
import sys
import json
import shutil
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from crew_config import create_stock_tracker_crew


def main():
    """Main execution function."""

    # Load environment variables from .env file
    load_dotenv()

    # Check for required API keys
    if not os.getenv("OPENROUTER_API_KEY"):
        print("ERROR: OPENROUTER_API_KEY not found in environment variables.")
        print("Please create a .env file with your OpenRouter API key:")
        print("  OPENROUTER_API_KEY=your-api-key-here")
        print()
        print("Get your free API key at: https://openrouter.ai/keys")
        sys.exit(1)

    print("="  * 70)
    print("  Joseph Carlson Show Stock Tracker - Automated Update")
    print("=" * 70)
    print()

    # Log runtime configuration
    print("Runtime Configuration:")
    print(f"  OpenRouter API Key: {'*' * 10 + os.getenv('OPENROUTER_API_KEY')[-4:] if os.getenv('OPENROUTER_API_KEY') else 'NOT SET'}")
    print(f"  Model: {os.getenv('CREW_MODEL', 'Not specified')}")
    print(f"  Tickers: {os.getenv('CREW_TICKERS', 'Not specified')}")
    print("=" * 70)
    print()

    # Create and run the crew
    try:
        crew = create_stock_tracker_crew()
        result = crew.kickoff()

        print()
        print("=" * 70)
        print("  Success! Stock data has been updated.")
        print("=" * 70)
        print()

        # Normalize lastUpdated values before copying
        output_file = Path("output/stocks.json")
        fetched_prices_file = Path("output/fetched_prices.json")
        website_data_file = Path("../data/stocks.json")

        if output_file.exists():
            today = datetime.utcnow().strftime("%Y-%m-%d")
            try:
                raw_text = output_file.read_text(encoding="utf-8").strip()

                # Remove accidental Markdown code fences (```json ... ```)
                if raw_text.startswith("```"):
                    raw_text = raw_text.split("\n", 1)[1] if "\n" in raw_text else ""
                if raw_text.endswith("```"):
                    raw_text = raw_text.rsplit("\n", 1)[0]

                data = json.loads(raw_text)

                existing_initial_prices = {}
                if website_data_file.exists():
                    try:
                        prior = json.loads(website_data_file.read_text(encoding="utf-8"))
                        if isinstance(prior, list):
                            for entry in prior:
                                if isinstance(entry, dict):
                                    ticker = (entry.get("ticker") or "").upper()
                                    if ticker and isinstance(entry.get("initialPrice"), (int, float)):
                                        existing_initial_prices[ticker] = entry["initialPrice"]
                    except Exception as e:
                        print(f"WARNING: Could not load existing initial prices ({e})")

                fetched_prices = {}
                if fetched_prices_file.exists():
                    try:
                        fetched_blob = json.loads(fetched_prices_file.read_text(encoding="utf-8"))
                        raw_prices = fetched_blob.get("prices", {})
                        if isinstance(raw_prices, dict):
                            for ticker, value in raw_prices.items():
                                if value is None:
                                    continue
                                try:
                                    fetched_prices[ticker.upper()] = round(float(value), 2)
                                except (TypeError, ValueError):
                                    continue
                        print(f"✓ Loaded {len(fetched_prices)} fetched price snapshots")
                    except Exception as e:
                        print(f"WARNING: Could not load fetched prices ({e})")
                else:
                    print("WARNING: fetched_prices.json not found, using formatter prices")

                updated = False
                price_updates = 0
                initial_assignments = 0
                if isinstance(data, list):
                    for entry in data:
                        if not isinstance(entry, dict):
                            continue

                        ticker = (entry.get("ticker") or "").upper()

                        if ticker:
                            fetched = fetched_prices.get(ticker)
                            if fetched is not None and entry.get("price") != fetched:
                                entry["price"] = fetched
                                price_updates += 1

                            prev_initial = existing_initial_prices.get(ticker)
                            if isinstance(prev_initial, (int, float)):
                                entry["initialPrice"] = prev_initial
                            else:
                                if "initialPrice" not in entry or not isinstance(entry["initialPrice"], (int, float)):
                                    entry["initialPrice"] = entry.get("price")
                                    initial_assignments += 1

                        if entry.get("lastUpdated") != today:
                            entry["lastUpdated"] = today
                            updated = True

                if updated or price_updates or initial_assignments:
                    output_file.write_text(
                        json.dumps(data, indent=2) + "\n", encoding="utf-8"
                    )
                    print(f"✓ Normalized lastUpdated fields to {today}")
                    if price_updates:
                        print(f"✓ Overwrote price field for {price_updates} tickers using fetched snapshots")
                    if initial_assignments:
                        print(f"✓ Assigned initialPrice for {initial_assignments} tickers")
            except Exception as e:
                print(f"WARNING: Could not normalize lastUpdated fields ({e})")

            # Create parent directory if it doesn't exist
            website_data_file.parent.mkdir(parents=True, exist_ok=True)

            # Copy the file
            shutil.copy(output_file, website_data_file)
            print(f"✓ Copied stocks.json to {website_data_file}")
            print()
            print("The website will now display the updated data.")
        else:
            print("WARNING: output/stocks.json was not created.")
            print("Please check the agent outputs above for errors.")

    except Exception as e:
        print()
        print("=" * 70)
        print("  ERROR: Failed to update stock data")
        print("=" * 70)
        print(f"\n{str(e)}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
