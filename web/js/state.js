// Shared state — avoids circular imports between map.js and scroll.js

let _lockY = null;
let _scrollHandler = null;

export function enableScrollLock(lockY) {
  _lockY = lockY !== undefined ? lockY : window.scrollY;
  _scrollHandler = () => {
    if (_lockY !== null && window.scrollY > _lockY) {
      window.scrollTo(0, _lockY);
    }
  };
  window.addEventListener("scroll", _scrollHandler);
}

export function disableScrollLock() {
  _lockY = null;
  if (_scrollHandler) {
    window.removeEventListener("scroll", _scrollHandler);
    _scrollHandler = null;
  }
}
