"""
# decorators.py
v. 2023-09-03
"""
import time


def retry(max_attempts=3, delay_seconds=5):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    result = func(*args, **kwargs)  # calls the target function
                    return result  # ends declarator in case of success

                except Exception as e:
                    if attempt < max_attempts:
                        print(
                            f"INFO  - Attempt {attempt}/{max_attempts} failed with error: {e}. \
Retrying in {delay_seconds}\" ...")
                        time.sleep(delay_seconds)
                    else:
                        print(f"Function {func.__name__} exceeded max retry attempts. Last error: {e}")
                        raise
        return wrapper
    return decorator
