import { useEffect, useState } from "react";

const App = (): React.JSX.Element => {
  const [version, setVersion] = useState<string>("讀取版本中");

  useEffect(() => {
    let isMounted = true;

    window.bridge.getAppVersion().then((appVersion) => {
      if (isMounted) {
        setVersion(appVersion);
      }
    });

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <main className="shell">
      <section className="placeholder" aria-labelledby="app-title">
        <p className="eyebrow">Desktop shell</p>
        <h1 id="app-title">VisionForge — 施工中</h1>
        <p className="version">v{version}</p>
      </section>
    </main>
  );
};

export default App;
