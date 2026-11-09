# Barriers

## Overview

A barrier repeats an action, or waits on it, until its effect arrives. Use one wherever a test would otherwise sleep.

## Pick A Barrier

| Effect | Barrier |
|--------|---------|
| The click loads a new page. | Use `demo.follow`, or [`trigger_until_navigation`][limelight.trigger_until_navigation] for a trigger that is not a link. |
| The click sends a request you can name. | Use [`trigger_until_response`][limelight.trigger_until_response]. |
| The click shows or reveals an element. | Use [`trigger_until_visible`][limelight.trigger_until_visible]. |
| The click starts background requests with no navigation. | Use [`requests_settled`][limelight.requests_settled]. |
| A condition outside the page changes. | Use [`demo.wait_until`][limelight.Demo.wait_until]. |

Each `trigger_until` function takes a callable and repeats it, and the last attempt raises. The `trigger_until_response` function matches a response by `url_fragment`, by `method`, or by `predicate`, and it takes exactly one of the three. The `requests_settled` context manager waits for the requests a URL fragment names. A barrier that never sees its effect raises [`BarrierError`][limelight.BarrierError], with the last Playwright timeout as its cause.

```python
trigger_until_response(page, lambda: demo.click(submit), method='POST')

with requests_settled(page, url_fragment='/orders/'):
    demo.click(save)
```

A `spotlight`, a `narrate`, a `title`, and a `pause` return at once in a silent run, so none of them is a barrier.

## Use Them Safely

- **Retries**: A barrier repeats whatever you hand it, so a form post that outlasts `timeout_ms` is sent again. Pass `attempt_count_max=1` for an action that must only happen once.
- **Narrated clicks**: The pointer spends part of `timeout_ms` on its approach, so give a barrier around a narrated click more room.
- **Debounced requests**: A block only counts what starts inside it, so follow it with an `expect` on the result.
