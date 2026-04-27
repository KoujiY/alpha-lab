import "fake-indexeddb/auto";
import "@testing-library/jest-dom/vitest";

// jsdom 缺 ResizeObserver，Radix Slider / Popover 等 primitive 會呼叫
// useSize → 直接 new ResizeObserver() 炸 ReferenceError。給一個 noop stub。
class ResizeObserverStub implements ResizeObserver {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}
if (typeof globalThis.ResizeObserver === "undefined") {
  globalThis.ResizeObserver = ResizeObserverStub as unknown as typeof ResizeObserver;
}

// Radix 某些元件（Dialog / Popover）會用 hasPointerCapture → jsdom 沒這方法
if (typeof Element !== "undefined") {
  if (!Element.prototype.hasPointerCapture) {
    Element.prototype.hasPointerCapture = () => false;
  }
  if (!Element.prototype.scrollIntoView) {
    Element.prototype.scrollIntoView = () => {};
  }
}
