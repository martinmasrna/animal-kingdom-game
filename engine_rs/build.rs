//! Embeds AK_SOURCE_HASH: FNV-1a 64 over the crate's game sources (Cargo.toml, then every src/**/*.rs in path order but
//! the two modules' glue, src/py.rs and src/wasm.rs, and the timing binary, src/bin/; each as its relative path, a zero
//! byte, its bytes, a zero byte). The browser's wasm and the server's module are the same
//! game only when their hashes agree; `/api/local/engine` reports the server's (`ak_engine.source_hash()`).
use std::path::{Path, PathBuf};

fn walk(dir: &Path, out: &mut Vec<PathBuf>) {
    for e in std::fs::read_dir(dir).unwrap() {
        let p = e.unwrap().path();
        if p.is_dir() {
            walk(&p, out);
        } else if p.extension().map_or(false, |x| x == "rs") {
            out.push(p);
        }
    }
}

fn main() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let mut files = Vec::new();
    walk(&root.join("src"), &mut files);
    let mut rel: Vec<String> = files.iter().map(|p| p.strip_prefix(root).unwrap().to_string_lossy().replace('\\', "/")).collect();
    rel.retain(|r| r != "src/py.rs" && r != "src/wasm.rs" && !r.starts_with("src/bin/"));
    rel.sort();
    rel.insert(0, "Cargo.toml".into());
    let mut h: u64 = 0xcbf29ce484222325;
    let mut feed = |b: &[u8]| {
        for &x in b {
            h ^= x as u64;
            h = h.wrapping_mul(0x100000001b3);
        }
    };
    for r in &rel {
        feed(r.as_bytes());
        feed(&[0]);
        // line endings as committed: a checkout with CRLF (the Windows PC) hashes as the LF one does
        let text = std::fs::read(root.join(r)).unwrap();
        let text: Vec<u8> = text.into_iter().filter(|&c| c != b'\r').collect();
        feed(&text);
        feed(&[0]);
    }
    println!("cargo:rustc-env=AK_SOURCE_HASH={h:016x}");
    println!("cargo:rerun-if-changed=src");
    println!("cargo:rerun-if-changed=Cargo.toml");
}
