import React, { useEffect, useState } from 'react';

const AuroraBackground = () => {
  const [AuroraComponent, setAuroraComponent] = useState(null);

  useEffect(() => {
    let isMounted = true;
    const componentName = (window && window.__AURORA_COMPONENT__) || 'Aurora';

    import(`./${componentName}`)
      .then((module) => {
        if (!isMounted) {
          return;
        }
        const Component = module.default || module.Aurora || null;
        setAuroraComponent(() => Component);
      })
      .catch(() => {
        if (isMounted) {
          setAuroraComponent(null);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="aurora-background-layer" aria-hidden="true">
      {AuroraComponent ? <AuroraComponent /> : <div className="aurora-fallback" />}
    </div>
  );
};

export default AuroraBackground;
