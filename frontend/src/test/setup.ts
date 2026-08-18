import "@testing-library/jest-dom/vitest";
import { afterEach, beforeAll } from "vitest";
import { cleanup } from "@testing-library/react";

beforeAll(() => {
  Object.defineProperty(window, "scrollTo", { value: () => undefined, writable: true });
});

afterEach(() => {
  cleanup();
  window.location.hash = "#/";
});
