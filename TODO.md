# TODO

## Performance: inline JSON size scaling

Currently all walk data (including track points) is embedded as inline JSON in
index.html. At ~90 KB per walk this will become a problem:

- 50 walks: ~4.5 MB
- 100 walks: ~9 MB
- 200 walks: ~18 MB

Options when this becomes noticeable:

1. **Simplify tracks** — downsample points (e.g. Douglas-Peucker). Walking GPS
   tracks are heavily oversampled for display; could cut 80%+ with no visible
   difference. Easy win, do first.
2. **Separate JSON file** — move walk data to `data.json`, fetch async. Enables
   browser caching.
3. **Lazy-load per walk** — one JSON file per walk, load track points only when
   clicked in the sidebar. Grid data stays inline.
