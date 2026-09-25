import { useEffect, useState } from "react";

const getWidth = () => {
  if (typeof window === "undefined") return 1024;
  return window.innerWidth;
};

const useResponsive = () => {
  const [windowWidth, setWindowWidth] = useState(getWidth);

  useEffect(() => {
    const handleResize = () => setWindowWidth(getWidth());

    window.addEventListener("resize", handleResize);
    handleResize();

    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const isMobile = windowWidth <= 640;
  const isTablet = windowWidth > 640 && windowWidth <= 1024;
  const isDesktop = windowWidth > 1024;

  return { isMobile, isTablet, isDesktop, windowWidth };
};

export default useResponsive;
