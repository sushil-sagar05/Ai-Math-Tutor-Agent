import { useEffect } from 'react';

function scrollToRefSafely(ref, options) {
  if (!ref.current) return;
  const rect = ref.current.getBoundingClientRect();
  const windowHeight = window.innerHeight || document.documentElement.clientHeight;
  
  const isInView = (
    rect.top >= 0 &&
    rect.bottom <= windowHeight
  );
  if (!isInView) {
    ref.current.scrollIntoView(options);
  }
}

export function useScrollToElement(ref, dependency, options = {}) {
  const {
    condition = () => true,
    delay = 0,
    options: scrollOptions = { behavior: 'smooth', block: 'nearest' }
  } = options;

  useEffect(() => {
    if (condition(dependency)) {
      const timer = setTimeout(() => {
        scrollToRefSafely(ref, scrollOptions);
      }, delay);

      return () => clearTimeout(timer);
    }
  }, [ref, dependency, condition, delay, scrollOptions]);
}
