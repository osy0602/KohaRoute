"""Unit tests for the login throttle, using a fake clock (no sleeping)."""

from app.services.login_throttle import LoginThrottle


class FakeClock:
    """A clock the test can move forward by hand."""

    def __init__(self) -> None:
        """Start at an arbitrary time."""
        self.now = 1000.0

    def __call__(self) -> float:
        """Return the current fake time."""
        return self.now


def make_throttle(clock: FakeClock) -> LoginThrottle:
    """Build a throttle with the real limits: 5 failures in 15 minutes."""
    return LoginThrottle(max_failures=5, window_seconds=900, clock=clock)


def test_blocks_after_five_failures():
    """The fifth failure triggers the block, the fourth does not."""
    throttle = make_throttle(FakeClock())
    for _ in range(4):
        throttle.record_failure("a@x.nz")
    assert throttle.is_blocked("a@x.nz") is False
    throttle.record_failure("a@x.nz")
    assert throttle.is_blocked("a@x.nz") is True


def test_other_emails_are_not_affected():
    """Failures are counted per email."""
    throttle = make_throttle(FakeClock())
    for _ in range(5):
        throttle.record_failure("a@x.nz")
    assert throttle.is_blocked("b@x.nz") is False


def test_block_expires_when_the_window_passes():
    """After 15 minutes the old failures no longer count."""
    clock = FakeClock()
    throttle = make_throttle(clock)
    for _ in range(5):
        throttle.record_failure("a@x.nz")
    clock.now += 901
    assert throttle.is_blocked("a@x.nz") is False


def test_retry_after_counts_down_from_the_oldest_failure():
    """Retry-After is the time left until the oldest failure leaves the window."""
    clock = FakeClock()
    throttle = make_throttle(clock)
    for _ in range(5):
        throttle.record_failure("a@x.nz")
    clock.now += 600
    assert throttle.retry_after_seconds("a@x.nz") == 300


def test_reset_clears_the_failures():
    """A successful login wipes the count."""
    throttle = make_throttle(FakeClock())
    for _ in range(5):
        throttle.record_failure("a@x.nz")
    throttle.reset("a@x.nz")
    assert throttle.is_blocked("a@x.nz") is False
