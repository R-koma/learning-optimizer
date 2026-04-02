"use client";

import { createContext, useContext, useState, ReactNode } from "react";

interface NavbarSlotContextValue {
  navbarCenter: ReactNode;
  setNavbarCenter: (node: ReactNode) => void;
}

export const NavbarSlotContext = createContext<NavbarSlotContextValue>({
  navbarCenter: null,
  setNavbarCenter: () => {},
});

export function NavbarSlotProvider({ children }: { children: ReactNode }) {
  const [navbarCenter, setNavbarCenter] = useState<ReactNode>(null);
  return (
    <NavbarSlotContext.Provider value={{ navbarCenter, setNavbarCenter }}>
      {children}
    </NavbarSlotContext.Provider>
  );
}

export const useNavbarSlot = () => useContext(NavbarSlotContext);
