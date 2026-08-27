# Changelog

## 0.2.0

- `DEMO_VIDEO` renders the narrated run frame by frame instead of recording the screen: the browser runs headless under
  Chrome's begin-frame control, `FrameRenderer` drives the compositor one frame at a time and pipes every frame into
  ffmpeg, and `video.mp4` lands beside the transcript at 3840x2160 and 60 fps regardless of machine speed. Frames
  are captured as JPEG at quality 100 by default; `screenshot_format` and `screenshot_quality` select PNG or WebP.
  The frame clock pauses while the main frame navigates, since a frame issued during a renderer process swap is
  never answered.
- The overlay takes a frame clock in video mode, so holds, cursor glides, typing and slides are measured in frames.
- `limelight-render` burns subtitles only with `--subtitles`, accepts `video.mp4` as its source, and skips re-encoding
  when there is nothing to add.
- The cursor glide keys off the animation-frame timestamp instead of the wall clock.
- The root package exports only the names a demo author writes. Removed from the root, and breaking: `BEAT_MS_DEFAULT`,
  `DIRECTION_DOWN`, `DIRECTION_UP`, `LAUNCH_ARGUMENTS_FRAME_CONTROL`, `NAV_WAIT_TIMEOUT_MS`, `VIDEO_FILE_NAME`,
  `Camera`, `DirectorySink`, `FrameRenderer`, `Overlay`, `Presenter`, `PresenterNarrated`, `PresenterSilent`,
  `Transcript`, `VideoSink`, `endpoint_free`, `launch_arguments_frame_control`, `presenter_build`, `renderer_for`,
  `renderer_register`, `renderer_unregister`. Each is still importable from its own module.
- `DemoSession.start` no longer takes a `presenter`; it always builds one from the config. `DemoSession.__init__`
  keeps the keyword as the testing seam.
- `DemoSession.__init__` calls `scenes_prepare()` once the navigator exists. A subclass attaches its scenes there
  instead of overriding `__init__` and naming a presenter in its signature.
- `limelight.django` is a package. `DjangoApplication.with_user` builds `type(self)` rather than the base class, and
  `url()` merges the new `url_kwargs_defaults()` underneath the caller's kwargs, which is what a multi-tenant
  subclass needs.
- `limelight.django` gains `sign_in`, `wait_until`, and a `limelight.django.server` module carrying the sequential
  WSGI server that keeps an in-memory sqlite database from deadlocking under a threaded live server.
- New `limelight.django.pytest_plugin`: a `live_server` that swaps in the sequential thread for in-memory sqlite, a
  `page` carrying a navigation timeout from `demo_navigation_timeout_ms`, and `DJANGO_ALLOW_ASYNC_UNSAFE`.
- The narrated browser context declares `no_viewport` itself rather than inheriting it from whatever fixture sits
  below it in the chain, so a narrated run fills the real window with no consumer plugin underneath.
- `limelight.pytest_plugin` owns window sizing through the new `demo_window_size` fixture. `browser_context_args_for`
  and `browser_type_launch_args_for` are private; consumers override the fixtures rather than rewiring them.
- `trigger_until_navigation` takes `url_pattern` as an option rather than a requirement, for a barrier that only
  needs the navigation to happen.
- `trigger_until_response` takes a `predicate` as an alternative to `url_fragment`, for a barrier that keys off the
  request method or off more than one part of the URL. Exactly one of the two is required.
- `Modal` and `SearchAndSelect` read their selectors from class attributes (`root_selector`, `choice_selector`,
  `dropdown_selector`, `search_placeholder`, `toggle_selector`), so different markup is a subclass rather than a
  rewrite.
- Demo artifacts (screenshots, transcript, video) land under `.demos/` instead of `test-results/`.
  pytest-playwright clears `test-results/` at session start, so any concurrent pytest run used to delete a
  recording in progress; `.demos/` belongs to limelight alone. Breaking for anything that read the old path.
- Narrated clicks, checks, unchecks, and hovers are driven by the real mouse at the exact point the animated
  cursor lands on, so the visible cursor and the dispatched events can no longer disagree. A hit test guards the
  press: when another element covers the point, the action falls back to the locator so nothing silently
  misfires. `force=True` presses the mouse without the hit test.
- `select` renders the dropdown the native popup never shows: the overlay draws the option list under the field,
  the cursor glides to the chosen option, the option highlights, and only then does the value change. Fields
  that are not a `<select>`, or an option the field does not carry, fall back to the plain `select_option`.
- `shot` shows the cursor again after hiding it for the screenshot; it used to stay invisible until the next
  glide.
- Video mode keeps animating after mid-demo navigations. The frame clock advanced only in video time while
  the wall clock ran ahead, so once the gap outgrew the 60s lead, any newly navigated document received frame
  times below its own timeline zero: `requestAnimationFrame` timestamps froze, and every cursor glide, overlay
  fade, and CSS transition on that page rendered as invisible or stuck while screenshots kept flowing. The
  renderer now re-pegs its frame clock to real time after each navigation, the cursor glide advances by frame
  count when timestamps stall, and the overlay drops its transitions entirely on a page whose clock is frozen.
- The cursor position survives navigation: on a fresh page the cursor glides in from where it was on the page
  before (or from the viewport centre on first appearance) instead of materialising on its target, so the first
  click after every page load is a visible movement. Short hops also pace no faster than half the reference
  duration, so a click on an adjacent control still reads as travel.
- Breaking: `Modal`, `SearchAndSelect`, and `SlideButton` take the `DemoSession` first (`Modal(demo)`,
  `SearchAndSelect(demo, root)`, `SearchAndSelect.within(demo, container)`, `SlideButton(demo)`) and route every
  action through the presenter, so component-driven modals and dropdowns are opened by the visible cursor
  instead of by invisible programmatic clicks.


## 0.1.0

- Initial release
