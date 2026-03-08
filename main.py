"""
Job Auto-Apply Bot - Main Entry Point
Applies to 50+ jobs daily across LinkedIn, Indeed, and Dice.

Usage:
    python main.py              # Run all platforms
    python main.py --linkedin   # LinkedIn only
    python main.py --indeed     # Indeed only
    python main.py --dice       # Dice only
    python main.py --schedule   # Run daily at scheduled time
"""
import sys
import argparse
import schedule
import time
from datetime import datetime

from browser_setup import create_driver
from linkedin_bot import LinkedInBot
from indeed_bot import IndeedBot
from dice_bot import DiceBot
from tracker import get_today_count
from utils import logger


def run_linkedin(driver):
    try:
        bot = LinkedInBot(driver)
        return bot.run()
    except Exception as e:
        logger.error(f"LinkedIn bot crashed: {e}")
        return 0


def run_indeed(driver):
    try:
        bot = IndeedBot(driver)
        return bot.run()
    except Exception as e:
        logger.error(f"Indeed bot crashed: {e}")
        return 0


def run_dice(driver):
    try:
        bot = DiceBot(driver)
        return bot.run()
    except Exception as e:
        logger.error(f"Dice bot crashed: {e}")
        return 0


def run_all():
    logger.info("=" * 70)
    logger.info(f"  JOB AUTO-APPLY BOT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"  Already applied today: {get_today_count()}")
    logger.info("=" * 70)

    driver = None
    total = 0

    try:
        driver = create_driver()

        # Run LinkedIn
        logger.info("\n>>> Starting LinkedIn Easy Apply...")
        linkedin_count = run_linkedin(driver)
        total += linkedin_count

        # Run Indeed
        logger.info("\n>>> Starting Indeed Auto-Apply...")
        indeed_count = run_indeed(driver)
        total += indeed_count

        # Run Dice
        logger.info("\n>>> Starting Dice Auto-Apply...")
        dice_count = run_dice(driver)
        total += dice_count

        logger.info("\n" + "=" * 70)
        logger.info(f"  SESSION COMPLETE")
        logger.info(f"  LinkedIn: {linkedin_count} | Indeed: {indeed_count} | Dice: {dice_count}")
        logger.info(f"  Total applied this session: {total}")
        logger.info(f"  Total applied today: {get_today_count()}")
        logger.info("=" * 70)

    except Exception as e:
        logger.error(f"Bot error: {e}")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    return total


def run_single_platform(platform):
    driver = None
    try:
        driver = create_driver()

        if platform == "linkedin":
            count = run_linkedin(driver)
        elif platform == "indeed":
            count = run_indeed(driver)
        elif platform == "dice":
            count = run_dice(driver)
        else:
            logger.error(f"Unknown platform: {platform}")
            return 0

        logger.info(f"\n{platform.title()}: Applied to {count} jobs this session")
        logger.info(f"Total applied today: {get_today_count()}")
        return count

    except Exception as e:
        logger.error(f"Bot error: {e}")
        return 0
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


def scheduled_run():
    logger.info("Scheduled run triggered!")
    run_all()


def main():
    parser = argparse.ArgumentParser(description="Job Auto-Apply Bot")
    parser.add_argument("--linkedin", action="store_true", help="Run LinkedIn only")
    parser.add_argument("--indeed", action="store_true", help="Run Indeed only")
    parser.add_argument("--dice", action="store_true", help="Run Dice only")
    parser.add_argument("--schedule", action="store_true", help="Run daily at 9 AM")
    parser.add_argument("--time", type=str, default="09:00", help="Schedule time (HH:MM)")
    args = parser.parse_args()

    if args.schedule:
        logger.info(f"Scheduling daily job applications at {args.time}")
        schedule.every().day.at(args.time).do(scheduled_run)

        # Also run immediately
        scheduled_run()

        while True:
            schedule.run_pending()
            time.sleep(60)

    elif args.linkedin:
        run_single_platform("linkedin")
    elif args.indeed:
        run_single_platform("indeed")
    elif args.dice:
        run_single_platform("dice")
    else:
        run_all()


if __name__ == "__main__":
    main()
