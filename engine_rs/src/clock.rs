//! The bots' clock: `std::time::Instant` natively; on wasm32, where `Instant::now` panics, the browser's `Date.now()`
//! behind the same few methods the search uses (now, elapsed, a deadline as now + duration, comparison).

#[cfg(not(target_arch = "wasm32"))]
pub use std::time::Instant;

#[cfg(target_arch = "wasm32")]
pub use web::Instant;

#[cfg(target_arch = "wasm32")]
mod web {
    use std::time::Duration;

    /// Milliseconds since the epoch, as the browser reports them.
    #[derive(Clone, Copy, Debug, PartialEq, PartialOrd)]
    pub struct Instant(f64);

    impl Instant {
        pub fn now() -> Instant {
            Instant(js_sys::Date::now())
        }
        pub fn elapsed(&self) -> Duration {
            Duration::from_secs_f64(((js_sys::Date::now() - self.0) / 1000.0).max(0.0))
        }
    }

    impl std::ops::Add<Duration> for Instant {
        type Output = Instant;
        fn add(self, d: Duration) -> Instant {
            Instant(self.0 + d.as_secs_f64() * 1000.0)
        }
    }
}
