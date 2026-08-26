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

## 0.1.0

- Initial release
