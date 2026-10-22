//! Python's `random.Random`, bit for bit: MT19937 seeded the way CPython seeds an int, `random()`,
//! `getrandbits`, `_randbelow`, `shuffle`, `choice` and `sample` with CPython's algorithms, and the
//! 625-word state tuple `getstate()` returns, so a Rust game serialises to the same `rng` dict as a
//! Python one and a Python-saved game resumes with the same stream.

const N: usize = 624;
const M: usize = 397;
const MATRIX_A: u32 = 0x9908b0df;
const UPPER: u32 = 0x80000000;
const LOWER: u32 = 0x7fffffff;

#[derive(Clone, Debug)]
pub struct PyRandom {
    mt: [u32; N],
    index: usize,
}

impl PyRandom {
    fn init_genrand(&mut self, s: u32) {
        self.mt[0] = s;
        for i in 1..N {
            self.mt[i] = 1812433253u32
                .wrapping_mul(self.mt[i - 1] ^ (self.mt[i - 1] >> 30))
                .wrapping_add(i as u32);
        }
        self.index = N;
    }

    fn init_by_array(&mut self, key: &[u32]) {
        self.init_genrand(19650218);
        let mut i = 1usize;
        let mut j = 0usize;
        let klen = key.len().max(1);
        let mut k = if N > klen { N } else { klen };
        while k > 0 {
            let prev = self.mt[i - 1] ^ (self.mt[i - 1] >> 30);
            self.mt[i] = (self.mt[i] ^ prev.wrapping_mul(1664525))
                .wrapping_add(key[j])
                .wrapping_add(j as u32);
            i += 1;
            j += 1;
            if i >= N {
                self.mt[0] = self.mt[N - 1];
                i = 1;
            }
            if j >= key.len() {
                j = 0;
            }
            k -= 1;
        }
        k = N - 1;
        while k > 0 {
            let prev = self.mt[i - 1] ^ (self.mt[i - 1] >> 30);
            self.mt[i] = (self.mt[i] ^ prev.wrapping_mul(1566083941)).wrapping_sub(i as u32);
            i += 1;
            if i >= N {
                self.mt[0] = self.mt[N - 1];
                i = 1;
            }
            k -= 1;
        }
        self.mt[0] = 0x80000000;
        self.index = N;
    }

    /// `random.Random(seed)` for an int seed: the absolute value split into 32-bit words, least significant first.
    pub fn seeded(seed: i64) -> PyRandom {
        let mut r = PyRandom { mt: [0; N], index: N };
        let mut v = seed.unsigned_abs() as u128;
        let mut key: Vec<u32> = Vec::new();
        if v == 0 {
            key.push(0);
        }
        while v > 0 {
            key.push((v & 0xffff_ffff) as u32);
            v >>= 32;
        }
        r.init_by_array(&key);
        r
    }

    /// `random.Random(seed)` for an unsigned 64-bit seed (a `getrandbits(64)` value).
    pub fn seeded_u64(seed: u64) -> PyRandom {
        let mut r = PyRandom { mt: [0; N], index: N };
        let mut key: Vec<u32> = Vec::new();
        let mut v = seed;
        if v == 0 {
            key.push(0);
        }
        while v > 0 {
            key.push((v & 0xffff_ffff) as u32);
            v >>= 32;
        }
        r.init_by_array(&key);
        r
    }

    /// From the 625 words `getstate()` gives (624 state words and the index).
    pub fn from_state(words: &[i64]) -> PyRandom {
        let mut r = PyRandom { mt: [0; N], index: N };
        for i in 0..N {
            r.mt[i] = words[i] as u32;
        }
        r.index = words[N] as usize;
        r
    }

    pub fn state_words(&self) -> Vec<i64> {
        let mut out: Vec<i64> = self.mt.iter().map(|&w| w as i64).collect();
        out.push(self.index as i64);
        out
    }

    fn generate(&mut self) {
        for kk in 0..N - M {
            let y = (self.mt[kk] & UPPER) | (self.mt[kk + 1] & LOWER);
            self.mt[kk] = self.mt[kk + M] ^ (y >> 1) ^ if y & 1 != 0 { MATRIX_A } else { 0 };
        }
        for kk in N - M..N - 1 {
            let y = (self.mt[kk] & UPPER) | (self.mt[kk + 1] & LOWER);
            self.mt[kk] = self.mt[kk + M - N] ^ (y >> 1) ^ if y & 1 != 0 { MATRIX_A } else { 0 };
        }
        let y = (self.mt[N - 1] & UPPER) | (self.mt[0] & LOWER);
        self.mt[N - 1] = self.mt[M - 1] ^ (y >> 1) ^ if y & 1 != 0 { MATRIX_A } else { 0 };
        self.index = 0;
    }

    pub fn genrand_u32(&mut self) -> u32 {
        if self.index >= N {
            self.generate();
        }
        let mut y = self.mt[self.index];
        self.index += 1;
        y ^= y >> 11;
        y ^= (y << 7) & 0x9d2c5680;
        y ^= (y << 15) & 0xefc60000;
        y ^= y >> 18;
        y
    }

    /// `random()`: 53 random bits as a float in [0, 1).
    pub fn random(&mut self) -> f64 {
        let a = (self.genrand_u32() >> 5) as f64;
        let b = (self.genrand_u32() >> 6) as f64;
        (a * 67108864.0 + b) * (1.0 / 9007199254740992.0)
    }

    /// `getrandbits(k)` for k up to 64 (CPython fills 32-bit words least significant first).
    pub fn getrandbits(&mut self, k: u32) -> u64 {
        if k == 0 {
            return 0;
        }
        if k <= 32 {
            return (self.genrand_u32() >> (32 - k)) as u64;
        }
        let mut out: u64 = 0;
        let mut k = k;
        let mut shift = 0;
        while k > 0 {
            let mut r = self.genrand_u32();
            if k < 32 {
                r >>= 32 - k;
            }
            out |= (r as u64) << shift;
            shift += 32;
            k = k.saturating_sub(32);
        }
        out
    }

    /// `_randbelow(n)`: rejection sampling on `n.bit_length()` bits.
    pub fn randbelow(&mut self, n: usize) -> usize {
        if n == 0 {
            return 0;
        }
        let k = (usize::BITS - n.leading_zeros()) as u32;
        loop {
            let r = self.getrandbits(k) as usize;
            if r < n {
                return r;
            }
        }
    }

    /// `shuffle(x)`: Fisher-Yates from the end, as CPython does it.
    pub fn shuffle<T>(&mut self, x: &mut [T]) {
        let n = x.len();
        if n < 2 {
            return;
        }
        for i in (1..n).rev() {
            let j = self.randbelow(i + 1);
            x.swap(i, j);
        }
    }

    /// `choice(seq)`'s index.
    pub fn choice_index(&mut self, n: usize) -> usize {
        self.randbelow(n)
    }

    /// `sample(population, k)` as indexes into the population, CPython's two methods.
    pub fn sample_indexes(&mut self, n: usize, k: usize) -> Vec<usize> {
        let mut result = Vec::with_capacity(k);
        let mut setsize = 21usize;
        if k > 5 {
            // 4 ** ceil(log(k * 3, 4))
            let target = (k * 3) as f64;
            let mut p = 1usize;
            let mut e = 0u32;
            while (p as f64) < target {
                p *= 4;
                e += 1;
            }
            // log(k*3, 4) exact powers: ceil(log(x,4)) where x is an exact power of 4 is that power
            let _ = e;
            setsize += p;
        }
        if n <= setsize {
            let mut pool: Vec<usize> = (0..n).collect();
            for i in 0..k {
                let j = self.randbelow(n - i);
                result.push(pool[j]);
                pool[j] = pool[n - i - 1];
            }
        } else {
            let mut selected = std::collections::HashSet::new();
            for _ in 0..k {
                let mut j = self.randbelow(n);
                while selected.contains(&j) {
                    j = self.randbelow(n);
                }
                selected.insert(j);
                result.push(j);
            }
        }
        result
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn seeded_matches_cpython() {
        // python3 -c "import random; r=random.Random(42); print(r.random(), r.getrandbits(32))"
        let mut r = PyRandom::seeded(42);
        assert!((r.random() - 0.6394267984578837).abs() < 1e-15);
    }
}
