import React from 'react'
import { useInView } from 'react-intersection-observer'

const LazyImage = ({ width, height, src, className='', rootMargin='150px', ...rest }) => {
  const [ref, inView] = useInView({
    threshold: 0,
    triggerOnce: true,
    rootMargin: rootMargin
  });

  return (
    <div ref={ref} className={className}>
      {inView ? (
        <img {...rest} src={src} />
      ) : null}
    </div>
  )
};

export default LazyImage;