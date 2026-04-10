function getDefaultExportFromCjs(x2) {
  return x2 && x2.__esModule && Object.prototype.hasOwnProperty.call(x2, "default") ? x2["default"] : x2;
}
var jsxRuntime = { exports: {} };
var reactJsxRuntime_production_min = {};
var react = { exports: {} };
var react_production_min = {};
/**
 * @license React
 * react.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
var l$1 = Symbol.for("react.element"), n$1 = Symbol.for("react.portal"), p$2 = Symbol.for("react.fragment"), q$1 = Symbol.for("react.strict_mode"), r = Symbol.for("react.profiler"), t = Symbol.for("react.provider"), u = Symbol.for("react.context"), v$1 = Symbol.for("react.forward_ref"), w = Symbol.for("react.suspense"), x = Symbol.for("react.memo"), y = Symbol.for("react.lazy"), z$1 = Symbol.iterator;
function A$1(a) {
  if (null === a || "object" !== typeof a) return null;
  a = z$1 && a[z$1] || a["@@iterator"];
  return "function" === typeof a ? a : null;
}
var B$1 = { isMounted: function() {
  return false;
}, enqueueForceUpdate: function() {
}, enqueueReplaceState: function() {
}, enqueueSetState: function() {
} }, C$1 = Object.assign, D$1 = {};
function E$1(a, b, e) {
  this.props = a;
  this.context = b;
  this.refs = D$1;
  this.updater = e || B$1;
}
E$1.prototype.isReactComponent = {};
E$1.prototype.setState = function(a, b) {
  if ("object" !== typeof a && "function" !== typeof a && null != a) throw Error("setState(...): takes an object of state variables to update or a function which returns an object of state variables.");
  this.updater.enqueueSetState(this, a, b, "setState");
};
E$1.prototype.forceUpdate = function(a) {
  this.updater.enqueueForceUpdate(this, a, "forceUpdate");
};
function F() {
}
F.prototype = E$1.prototype;
function G$1(a, b, e) {
  this.props = a;
  this.context = b;
  this.refs = D$1;
  this.updater = e || B$1;
}
var H$1 = G$1.prototype = new F();
H$1.constructor = G$1;
C$1(H$1, E$1.prototype);
H$1.isPureReactComponent = true;
var I$1 = Array.isArray, J = Object.prototype.hasOwnProperty, K$1 = { current: null }, L$1 = { key: true, ref: true, __self: true, __source: true };
function M$1(a, b, e) {
  var d, c = {}, k2 = null, h = null;
  if (null != b) for (d in void 0 !== b.ref && (h = b.ref), void 0 !== b.key && (k2 = "" + b.key), b) J.call(b, d) && !L$1.hasOwnProperty(d) && (c[d] = b[d]);
  var g = arguments.length - 2;
  if (1 === g) c.children = e;
  else if (1 < g) {
    for (var f2 = Array(g), m2 = 0; m2 < g; m2++) f2[m2] = arguments[m2 + 2];
    c.children = f2;
  }
  if (a && a.defaultProps) for (d in g = a.defaultProps, g) void 0 === c[d] && (c[d] = g[d]);
  return { $$typeof: l$1, type: a, key: k2, ref: h, props: c, _owner: K$1.current };
}
function N$1(a, b) {
  return { $$typeof: l$1, type: a.type, key: b, ref: a.ref, props: a.props, _owner: a._owner };
}
function O$1(a) {
  return "object" === typeof a && null !== a && a.$$typeof === l$1;
}
function escape(a) {
  var b = { "=": "=0", ":": "=2" };
  return "$" + a.replace(/[=:]/g, function(a2) {
    return b[a2];
  });
}
var P$1 = /\/+/g;
function Q$1(a, b) {
  return "object" === typeof a && null !== a && null != a.key ? escape("" + a.key) : b.toString(36);
}
function R$1(a, b, e, d, c) {
  var k2 = typeof a;
  if ("undefined" === k2 || "boolean" === k2) a = null;
  var h = false;
  if (null === a) h = true;
  else switch (k2) {
    case "string":
    case "number":
      h = true;
      break;
    case "object":
      switch (a.$$typeof) {
        case l$1:
        case n$1:
          h = true;
      }
  }
  if (h) return h = a, c = c(h), a = "" === d ? "." + Q$1(h, 0) : d, I$1(c) ? (e = "", null != a && (e = a.replace(P$1, "$&/") + "/"), R$1(c, b, e, "", function(a2) {
    return a2;
  })) : null != c && (O$1(c) && (c = N$1(c, e + (!c.key || h && h.key === c.key ? "" : ("" + c.key).replace(P$1, "$&/") + "/") + a)), b.push(c)), 1;
  h = 0;
  d = "" === d ? "." : d + ":";
  if (I$1(a)) for (var g = 0; g < a.length; g++) {
    k2 = a[g];
    var f2 = d + Q$1(k2, g);
    h += R$1(k2, b, e, f2, c);
  }
  else if (f2 = A$1(a), "function" === typeof f2) for (a = f2.call(a), g = 0; !(k2 = a.next()).done; ) k2 = k2.value, f2 = d + Q$1(k2, g++), h += R$1(k2, b, e, f2, c);
  else if ("object" === k2) throw b = String(a), Error("Objects are not valid as a React child (found: " + ("[object Object]" === b ? "object with keys {" + Object.keys(a).join(", ") + "}" : b) + "). If you meant to render a collection of children, use an array instead.");
  return h;
}
function S$1(a, b, e) {
  if (null == a) return a;
  var d = [], c = 0;
  R$1(a, d, "", "", function(a2) {
    return b.call(e, a2, c++);
  });
  return d;
}
function T$1(a) {
  if (-1 === a._status) {
    var b = a._result;
    b = b();
    b.then(function(b2) {
      if (0 === a._status || -1 === a._status) a._status = 1, a._result = b2;
    }, function(b2) {
      if (0 === a._status || -1 === a._status) a._status = 2, a._result = b2;
    });
    -1 === a._status && (a._status = 0, a._result = b);
  }
  if (1 === a._status) return a._result.default;
  throw a._result;
}
var U$1 = { current: null }, V$1 = { transition: null }, W$1 = { ReactCurrentDispatcher: U$1, ReactCurrentBatchConfig: V$1, ReactCurrentOwner: K$1 };
function X$1() {
  throw Error("act(...) is not supported in production builds of React.");
}
react_production_min.Children = { map: S$1, forEach: function(a, b, e) {
  S$1(a, function() {
    b.apply(this, arguments);
  }, e);
}, count: function(a) {
  var b = 0;
  S$1(a, function() {
    b++;
  });
  return b;
}, toArray: function(a) {
  return S$1(a, function(a2) {
    return a2;
  }) || [];
}, only: function(a) {
  if (!O$1(a)) throw Error("React.Children.only expected to receive a single React element child.");
  return a;
} };
react_production_min.Component = E$1;
react_production_min.Fragment = p$2;
react_production_min.Profiler = r;
react_production_min.PureComponent = G$1;
react_production_min.StrictMode = q$1;
react_production_min.Suspense = w;
react_production_min.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED = W$1;
react_production_min.act = X$1;
react_production_min.cloneElement = function(a, b, e) {
  if (null === a || void 0 === a) throw Error("React.cloneElement(...): The argument must be a React element, but you passed " + a + ".");
  var d = C$1({}, a.props), c = a.key, k2 = a.ref, h = a._owner;
  if (null != b) {
    void 0 !== b.ref && (k2 = b.ref, h = K$1.current);
    void 0 !== b.key && (c = "" + b.key);
    if (a.type && a.type.defaultProps) var g = a.type.defaultProps;
    for (f2 in b) J.call(b, f2) && !L$1.hasOwnProperty(f2) && (d[f2] = void 0 === b[f2] && void 0 !== g ? g[f2] : b[f2]);
  }
  var f2 = arguments.length - 2;
  if (1 === f2) d.children = e;
  else if (1 < f2) {
    g = Array(f2);
    for (var m2 = 0; m2 < f2; m2++) g[m2] = arguments[m2 + 2];
    d.children = g;
  }
  return { $$typeof: l$1, type: a.type, key: c, ref: k2, props: d, _owner: h };
};
react_production_min.createContext = function(a) {
  a = { $$typeof: u, _currentValue: a, _currentValue2: a, _threadCount: 0, Provider: null, Consumer: null, _defaultValue: null, _globalName: null };
  a.Provider = { $$typeof: t, _context: a };
  return a.Consumer = a;
};
react_production_min.createElement = M$1;
react_production_min.createFactory = function(a) {
  var b = M$1.bind(null, a);
  b.type = a;
  return b;
};
react_production_min.createRef = function() {
  return { current: null };
};
react_production_min.forwardRef = function(a) {
  return { $$typeof: v$1, render: a };
};
react_production_min.isValidElement = O$1;
react_production_min.lazy = function(a) {
  return { $$typeof: y, _payload: { _status: -1, _result: a }, _init: T$1 };
};
react_production_min.memo = function(a, b) {
  return { $$typeof: x, type: a, compare: void 0 === b ? null : b };
};
react_production_min.startTransition = function(a) {
  var b = V$1.transition;
  V$1.transition = {};
  try {
    a();
  } finally {
    V$1.transition = b;
  }
};
react_production_min.unstable_act = X$1;
react_production_min.useCallback = function(a, b) {
  return U$1.current.useCallback(a, b);
};
react_production_min.useContext = function(a) {
  return U$1.current.useContext(a);
};
react_production_min.useDebugValue = function() {
};
react_production_min.useDeferredValue = function(a) {
  return U$1.current.useDeferredValue(a);
};
react_production_min.useEffect = function(a, b) {
  return U$1.current.useEffect(a, b);
};
react_production_min.useId = function() {
  return U$1.current.useId();
};
react_production_min.useImperativeHandle = function(a, b, e) {
  return U$1.current.useImperativeHandle(a, b, e);
};
react_production_min.useInsertionEffect = function(a, b) {
  return U$1.current.useInsertionEffect(a, b);
};
react_production_min.useLayoutEffect = function(a, b) {
  return U$1.current.useLayoutEffect(a, b);
};
react_production_min.useMemo = function(a, b) {
  return U$1.current.useMemo(a, b);
};
react_production_min.useReducer = function(a, b, e) {
  return U$1.current.useReducer(a, b, e);
};
react_production_min.useRef = function(a) {
  return U$1.current.useRef(a);
};
react_production_min.useState = function(a) {
  return U$1.current.useState(a);
};
react_production_min.useSyncExternalStore = function(a, b, e) {
  return U$1.current.useSyncExternalStore(a, b, e);
};
react_production_min.useTransition = function() {
  return U$1.current.useTransition();
};
react_production_min.version = "18.3.1";
{
  react.exports = react_production_min;
}
var reactExports = react.exports;
const React = /* @__PURE__ */ getDefaultExportFromCjs(reactExports);
/**
 * @license React
 * react-jsx-runtime.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
var f = reactExports, k = Symbol.for("react.element"), l = Symbol.for("react.fragment"), m$1 = Object.prototype.hasOwnProperty, n = f.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED.ReactCurrentOwner, p$1 = { key: true, ref: true, __self: true, __source: true };
function q(c, a, g) {
  var b, d = {}, e = null, h = null;
  void 0 !== g && (e = "" + g);
  void 0 !== a.key && (e = "" + a.key);
  void 0 !== a.ref && (h = a.ref);
  for (b in a) m$1.call(a, b) && !p$1.hasOwnProperty(b) && (d[b] = a[b]);
  if (c && c.defaultProps) for (b in a = c.defaultProps, a) void 0 === d[b] && (d[b] = a[b]);
  return { $$typeof: k, type: c, key: e, ref: h, props: d, _owner: n.current };
}
reactJsxRuntime_production_min.Fragment = l;
reactJsxRuntime_production_min.jsx = q;
reactJsxRuntime_production_min.jsxs = q;
{
  jsxRuntime.exports = reactJsxRuntime_production_min;
}
var jsxRuntimeExports = jsxRuntime.exports;
var client = {};
var reactDom = { exports: {} };
var reactDom_production_min = {};
var scheduler = { exports: {} };
var scheduler_production_min = {};
/**
 * @license React
 * scheduler.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
(function(exports$1) {
  function f2(a, b) {
    var c = a.length;
    a.push(b);
    a: for (; 0 < c; ) {
      var d = c - 1 >>> 1, e = a[d];
      if (0 < g(e, b)) a[d] = b, a[c] = e, c = d;
      else break a;
    }
  }
  function h(a) {
    return 0 === a.length ? null : a[0];
  }
  function k2(a) {
    if (0 === a.length) return null;
    var b = a[0], c = a.pop();
    if (c !== b) {
      a[0] = c;
      a: for (var d = 0, e = a.length, w2 = e >>> 1; d < w2; ) {
        var m2 = 2 * (d + 1) - 1, C2 = a[m2], n2 = m2 + 1, x2 = a[n2];
        if (0 > g(C2, c)) n2 < e && 0 > g(x2, C2) ? (a[d] = x2, a[n2] = c, d = n2) : (a[d] = C2, a[m2] = c, d = m2);
        else if (n2 < e && 0 > g(x2, c)) a[d] = x2, a[n2] = c, d = n2;
        else break a;
      }
    }
    return b;
  }
  function g(a, b) {
    var c = a.sortIndex - b.sortIndex;
    return 0 !== c ? c : a.id - b.id;
  }
  if ("object" === typeof performance && "function" === typeof performance.now) {
    var l2 = performance;
    exports$1.unstable_now = function() {
      return l2.now();
    };
  } else {
    var p2 = Date, q2 = p2.now();
    exports$1.unstable_now = function() {
      return p2.now() - q2;
    };
  }
  var r2 = [], t2 = [], u2 = 1, v2 = null, y2 = 3, z2 = false, A2 = false, B2 = false, D2 = "function" === typeof setTimeout ? setTimeout : null, E2 = "function" === typeof clearTimeout ? clearTimeout : null, F2 = "undefined" !== typeof setImmediate ? setImmediate : null;
  "undefined" !== typeof navigator && void 0 !== navigator.scheduling && void 0 !== navigator.scheduling.isInputPending && navigator.scheduling.isInputPending.bind(navigator.scheduling);
  function G2(a) {
    for (var b = h(t2); null !== b; ) {
      if (null === b.callback) k2(t2);
      else if (b.startTime <= a) k2(t2), b.sortIndex = b.expirationTime, f2(r2, b);
      else break;
      b = h(t2);
    }
  }
  function H2(a) {
    B2 = false;
    G2(a);
    if (!A2) if (null !== h(r2)) A2 = true, I2(J2);
    else {
      var b = h(t2);
      null !== b && K2(H2, b.startTime - a);
    }
  }
  function J2(a, b) {
    A2 = false;
    B2 && (B2 = false, E2(L2), L2 = -1);
    z2 = true;
    var c = y2;
    try {
      G2(b);
      for (v2 = h(r2); null !== v2 && (!(v2.expirationTime > b) || a && !M2()); ) {
        var d = v2.callback;
        if ("function" === typeof d) {
          v2.callback = null;
          y2 = v2.priorityLevel;
          var e = d(v2.expirationTime <= b);
          b = exports$1.unstable_now();
          "function" === typeof e ? v2.callback = e : v2 === h(r2) && k2(r2);
          G2(b);
        } else k2(r2);
        v2 = h(r2);
      }
      if (null !== v2) var w2 = true;
      else {
        var m2 = h(t2);
        null !== m2 && K2(H2, m2.startTime - b);
        w2 = false;
      }
      return w2;
    } finally {
      v2 = null, y2 = c, z2 = false;
    }
  }
  var N2 = false, O2 = null, L2 = -1, P2 = 5, Q2 = -1;
  function M2() {
    return exports$1.unstable_now() - Q2 < P2 ? false : true;
  }
  function R2() {
    if (null !== O2) {
      var a = exports$1.unstable_now();
      Q2 = a;
      var b = true;
      try {
        b = O2(true, a);
      } finally {
        b ? S2() : (N2 = false, O2 = null);
      }
    } else N2 = false;
  }
  var S2;
  if ("function" === typeof F2) S2 = function() {
    F2(R2);
  };
  else if ("undefined" !== typeof MessageChannel) {
    var T2 = new MessageChannel(), U2 = T2.port2;
    T2.port1.onmessage = R2;
    S2 = function() {
      U2.postMessage(null);
    };
  } else S2 = function() {
    D2(R2, 0);
  };
  function I2(a) {
    O2 = a;
    N2 || (N2 = true, S2());
  }
  function K2(a, b) {
    L2 = D2(function() {
      a(exports$1.unstable_now());
    }, b);
  }
  exports$1.unstable_IdlePriority = 5;
  exports$1.unstable_ImmediatePriority = 1;
  exports$1.unstable_LowPriority = 4;
  exports$1.unstable_NormalPriority = 3;
  exports$1.unstable_Profiling = null;
  exports$1.unstable_UserBlockingPriority = 2;
  exports$1.unstable_cancelCallback = function(a) {
    a.callback = null;
  };
  exports$1.unstable_continueExecution = function() {
    A2 || z2 || (A2 = true, I2(J2));
  };
  exports$1.unstable_forceFrameRate = function(a) {
    0 > a || 125 < a ? console.error("forceFrameRate takes a positive int between 0 and 125, forcing frame rates higher than 125 fps is not supported") : P2 = 0 < a ? Math.floor(1e3 / a) : 5;
  };
  exports$1.unstable_getCurrentPriorityLevel = function() {
    return y2;
  };
  exports$1.unstable_getFirstCallbackNode = function() {
    return h(r2);
  };
  exports$1.unstable_next = function(a) {
    switch (y2) {
      case 1:
      case 2:
      case 3:
        var b = 3;
        break;
      default:
        b = y2;
    }
    var c = y2;
    y2 = b;
    try {
      return a();
    } finally {
      y2 = c;
    }
  };
  exports$1.unstable_pauseExecution = function() {
  };
  exports$1.unstable_requestPaint = function() {
  };
  exports$1.unstable_runWithPriority = function(a, b) {
    switch (a) {
      case 1:
      case 2:
      case 3:
      case 4:
      case 5:
        break;
      default:
        a = 3;
    }
    var c = y2;
    y2 = a;
    try {
      return b();
    } finally {
      y2 = c;
    }
  };
  exports$1.unstable_scheduleCallback = function(a, b, c) {
    var d = exports$1.unstable_now();
    "object" === typeof c && null !== c ? (c = c.delay, c = "number" === typeof c && 0 < c ? d + c : d) : c = d;
    switch (a) {
      case 1:
        var e = -1;
        break;
      case 2:
        e = 250;
        break;
      case 5:
        e = 1073741823;
        break;
      case 4:
        e = 1e4;
        break;
      default:
        e = 5e3;
    }
    e = c + e;
    a = { id: u2++, callback: b, priorityLevel: a, startTime: c, expirationTime: e, sortIndex: -1 };
    c > d ? (a.sortIndex = c, f2(t2, a), null === h(r2) && a === h(t2) && (B2 ? (E2(L2), L2 = -1) : B2 = true, K2(H2, c - d))) : (a.sortIndex = e, f2(r2, a), A2 || z2 || (A2 = true, I2(J2)));
    return a;
  };
  exports$1.unstable_shouldYield = M2;
  exports$1.unstable_wrapCallback = function(a) {
    var b = y2;
    return function() {
      var c = y2;
      y2 = b;
      try {
        return a.apply(this, arguments);
      } finally {
        y2 = c;
      }
    };
  };
})(scheduler_production_min);
{
  scheduler.exports = scheduler_production_min;
}
var schedulerExports = scheduler.exports;
/**
 * @license React
 * react-dom.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
var aa = reactExports, ca = schedulerExports;
function p(a) {
  for (var b = "https://reactjs.org/docs/error-decoder.html?invariant=" + a, c = 1; c < arguments.length; c++) b += "&args[]=" + encodeURIComponent(arguments[c]);
  return "Minified React error #" + a + "; visit " + b + " for the full message or use the non-minified dev environment for full errors and additional helpful warnings.";
}
var da = /* @__PURE__ */ new Set(), ea = {};
function fa(a, b) {
  ha(a, b);
  ha(a + "Capture", b);
}
function ha(a, b) {
  ea[a] = b;
  for (a = 0; a < b.length; a++) da.add(b[a]);
}
var ia = !("undefined" === typeof window || "undefined" === typeof window.document || "undefined" === typeof window.document.createElement), ja = Object.prototype.hasOwnProperty, ka = /^[:A-Z_a-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD][:A-Z_a-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD\-.0-9\u00B7\u0300-\u036F\u203F-\u2040]*$/, la = {}, ma = {};
function oa(a) {
  if (ja.call(ma, a)) return true;
  if (ja.call(la, a)) return false;
  if (ka.test(a)) return ma[a] = true;
  la[a] = true;
  return false;
}
function pa(a, b, c, d) {
  if (null !== c && 0 === c.type) return false;
  switch (typeof b) {
    case "function":
    case "symbol":
      return true;
    case "boolean":
      if (d) return false;
      if (null !== c) return !c.acceptsBooleans;
      a = a.toLowerCase().slice(0, 5);
      return "data-" !== a && "aria-" !== a;
    default:
      return false;
  }
}
function qa(a, b, c, d) {
  if (null === b || "undefined" === typeof b || pa(a, b, c, d)) return true;
  if (d) return false;
  if (null !== c) switch (c.type) {
    case 3:
      return !b;
    case 4:
      return false === b;
    case 5:
      return isNaN(b);
    case 6:
      return isNaN(b) || 1 > b;
  }
  return false;
}
function v(a, b, c, d, e, f2, g) {
  this.acceptsBooleans = 2 === b || 3 === b || 4 === b;
  this.attributeName = d;
  this.attributeNamespace = e;
  this.mustUseProperty = c;
  this.propertyName = a;
  this.type = b;
  this.sanitizeURL = f2;
  this.removeEmptyString = g;
}
var z = {};
"children dangerouslySetInnerHTML defaultValue defaultChecked innerHTML suppressContentEditableWarning suppressHydrationWarning style".split(" ").forEach(function(a) {
  z[a] = new v(a, 0, false, a, null, false, false);
});
[["acceptCharset", "accept-charset"], ["className", "class"], ["htmlFor", "for"], ["httpEquiv", "http-equiv"]].forEach(function(a) {
  var b = a[0];
  z[b] = new v(b, 1, false, a[1], null, false, false);
});
["contentEditable", "draggable", "spellCheck", "value"].forEach(function(a) {
  z[a] = new v(a, 2, false, a.toLowerCase(), null, false, false);
});
["autoReverse", "externalResourcesRequired", "focusable", "preserveAlpha"].forEach(function(a) {
  z[a] = new v(a, 2, false, a, null, false, false);
});
"allowFullScreen async autoFocus autoPlay controls default defer disabled disablePictureInPicture disableRemotePlayback formNoValidate hidden loop noModule noValidate open playsInline readOnly required reversed scoped seamless itemScope".split(" ").forEach(function(a) {
  z[a] = new v(a, 3, false, a.toLowerCase(), null, false, false);
});
["checked", "multiple", "muted", "selected"].forEach(function(a) {
  z[a] = new v(a, 3, true, a, null, false, false);
});
["capture", "download"].forEach(function(a) {
  z[a] = new v(a, 4, false, a, null, false, false);
});
["cols", "rows", "size", "span"].forEach(function(a) {
  z[a] = new v(a, 6, false, a, null, false, false);
});
["rowSpan", "start"].forEach(function(a) {
  z[a] = new v(a, 5, false, a.toLowerCase(), null, false, false);
});
var ra = /[\-:]([a-z])/g;
function sa(a) {
  return a[1].toUpperCase();
}
"accent-height alignment-baseline arabic-form baseline-shift cap-height clip-path clip-rule color-interpolation color-interpolation-filters color-profile color-rendering dominant-baseline enable-background fill-opacity fill-rule flood-color flood-opacity font-family font-size font-size-adjust font-stretch font-style font-variant font-weight glyph-name glyph-orientation-horizontal glyph-orientation-vertical horiz-adv-x horiz-origin-x image-rendering letter-spacing lighting-color marker-end marker-mid marker-start overline-position overline-thickness paint-order panose-1 pointer-events rendering-intent shape-rendering stop-color stop-opacity strikethrough-position strikethrough-thickness stroke-dasharray stroke-dashoffset stroke-linecap stroke-linejoin stroke-miterlimit stroke-opacity stroke-width text-anchor text-decoration text-rendering underline-position underline-thickness unicode-bidi unicode-range units-per-em v-alphabetic v-hanging v-ideographic v-mathematical vector-effect vert-adv-y vert-origin-x vert-origin-y word-spacing writing-mode xmlns:xlink x-height".split(" ").forEach(function(a) {
  var b = a.replace(
    ra,
    sa
  );
  z[b] = new v(b, 1, false, a, null, false, false);
});
"xlink:actuate xlink:arcrole xlink:role xlink:show xlink:title xlink:type".split(" ").forEach(function(a) {
  var b = a.replace(ra, sa);
  z[b] = new v(b, 1, false, a, "http://www.w3.org/1999/xlink", false, false);
});
["xml:base", "xml:lang", "xml:space"].forEach(function(a) {
  var b = a.replace(ra, sa);
  z[b] = new v(b, 1, false, a, "http://www.w3.org/XML/1998/namespace", false, false);
});
["tabIndex", "crossOrigin"].forEach(function(a) {
  z[a] = new v(a, 1, false, a.toLowerCase(), null, false, false);
});
z.xlinkHref = new v("xlinkHref", 1, false, "xlink:href", "http://www.w3.org/1999/xlink", true, false);
["src", "href", "action", "formAction"].forEach(function(a) {
  z[a] = new v(a, 1, false, a.toLowerCase(), null, true, true);
});
function ta(a, b, c, d) {
  var e = z.hasOwnProperty(b) ? z[b] : null;
  if (null !== e ? 0 !== e.type : d || !(2 < b.length) || "o" !== b[0] && "O" !== b[0] || "n" !== b[1] && "N" !== b[1]) qa(b, c, e, d) && (c = null), d || null === e ? oa(b) && (null === c ? a.removeAttribute(b) : a.setAttribute(b, "" + c)) : e.mustUseProperty ? a[e.propertyName] = null === c ? 3 === e.type ? false : "" : c : (b = e.attributeName, d = e.attributeNamespace, null === c ? a.removeAttribute(b) : (e = e.type, c = 3 === e || 4 === e && true === c ? "" : "" + c, d ? a.setAttributeNS(d, b, c) : a.setAttribute(b, c)));
}
var ua = aa.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED, va = Symbol.for("react.element"), wa = Symbol.for("react.portal"), ya = Symbol.for("react.fragment"), za = Symbol.for("react.strict_mode"), Aa = Symbol.for("react.profiler"), Ba = Symbol.for("react.provider"), Ca = Symbol.for("react.context"), Da = Symbol.for("react.forward_ref"), Ea = Symbol.for("react.suspense"), Fa = Symbol.for("react.suspense_list"), Ga = Symbol.for("react.memo"), Ha = Symbol.for("react.lazy");
var Ia = Symbol.for("react.offscreen");
var Ja = Symbol.iterator;
function Ka(a) {
  if (null === a || "object" !== typeof a) return null;
  a = Ja && a[Ja] || a["@@iterator"];
  return "function" === typeof a ? a : null;
}
var A = Object.assign, La;
function Ma(a) {
  if (void 0 === La) try {
    throw Error();
  } catch (c) {
    var b = c.stack.trim().match(/\n( *(at )?)/);
    La = b && b[1] || "";
  }
  return "\n" + La + a;
}
var Na = false;
function Oa(a, b) {
  if (!a || Na) return "";
  Na = true;
  var c = Error.prepareStackTrace;
  Error.prepareStackTrace = void 0;
  try {
    if (b) if (b = function() {
      throw Error();
    }, Object.defineProperty(b.prototype, "props", { set: function() {
      throw Error();
    } }), "object" === typeof Reflect && Reflect.construct) {
      try {
        Reflect.construct(b, []);
      } catch (l2) {
        var d = l2;
      }
      Reflect.construct(a, [], b);
    } else {
      try {
        b.call();
      } catch (l2) {
        d = l2;
      }
      a.call(b.prototype);
    }
    else {
      try {
        throw Error();
      } catch (l2) {
        d = l2;
      }
      a();
    }
  } catch (l2) {
    if (l2 && d && "string" === typeof l2.stack) {
      for (var e = l2.stack.split("\n"), f2 = d.stack.split("\n"), g = e.length - 1, h = f2.length - 1; 1 <= g && 0 <= h && e[g] !== f2[h]; ) h--;
      for (; 1 <= g && 0 <= h; g--, h--) if (e[g] !== f2[h]) {
        if (1 !== g || 1 !== h) {
          do
            if (g--, h--, 0 > h || e[g] !== f2[h]) {
              var k2 = "\n" + e[g].replace(" at new ", " at ");
              a.displayName && k2.includes("<anonymous>") && (k2 = k2.replace("<anonymous>", a.displayName));
              return k2;
            }
          while (1 <= g && 0 <= h);
        }
        break;
      }
    }
  } finally {
    Na = false, Error.prepareStackTrace = c;
  }
  return (a = a ? a.displayName || a.name : "") ? Ma(a) : "";
}
function Pa(a) {
  switch (a.tag) {
    case 5:
      return Ma(a.type);
    case 16:
      return Ma("Lazy");
    case 13:
      return Ma("Suspense");
    case 19:
      return Ma("SuspenseList");
    case 0:
    case 2:
    case 15:
      return a = Oa(a.type, false), a;
    case 11:
      return a = Oa(a.type.render, false), a;
    case 1:
      return a = Oa(a.type, true), a;
    default:
      return "";
  }
}
function Qa(a) {
  if (null == a) return null;
  if ("function" === typeof a) return a.displayName || a.name || null;
  if ("string" === typeof a) return a;
  switch (a) {
    case ya:
      return "Fragment";
    case wa:
      return "Portal";
    case Aa:
      return "Profiler";
    case za:
      return "StrictMode";
    case Ea:
      return "Suspense";
    case Fa:
      return "SuspenseList";
  }
  if ("object" === typeof a) switch (a.$$typeof) {
    case Ca:
      return (a.displayName || "Context") + ".Consumer";
    case Ba:
      return (a._context.displayName || "Context") + ".Provider";
    case Da:
      var b = a.render;
      a = a.displayName;
      a || (a = b.displayName || b.name || "", a = "" !== a ? "ForwardRef(" + a + ")" : "ForwardRef");
      return a;
    case Ga:
      return b = a.displayName || null, null !== b ? b : Qa(a.type) || "Memo";
    case Ha:
      b = a._payload;
      a = a._init;
      try {
        return Qa(a(b));
      } catch (c) {
      }
  }
  return null;
}
function Ra(a) {
  var b = a.type;
  switch (a.tag) {
    case 24:
      return "Cache";
    case 9:
      return (b.displayName || "Context") + ".Consumer";
    case 10:
      return (b._context.displayName || "Context") + ".Provider";
    case 18:
      return "DehydratedFragment";
    case 11:
      return a = b.render, a = a.displayName || a.name || "", b.displayName || ("" !== a ? "ForwardRef(" + a + ")" : "ForwardRef");
    case 7:
      return "Fragment";
    case 5:
      return b;
    case 4:
      return "Portal";
    case 3:
      return "Root";
    case 6:
      return "Text";
    case 16:
      return Qa(b);
    case 8:
      return b === za ? "StrictMode" : "Mode";
    case 22:
      return "Offscreen";
    case 12:
      return "Profiler";
    case 21:
      return "Scope";
    case 13:
      return "Suspense";
    case 19:
      return "SuspenseList";
    case 25:
      return "TracingMarker";
    case 1:
    case 0:
    case 17:
    case 2:
    case 14:
    case 15:
      if ("function" === typeof b) return b.displayName || b.name || null;
      if ("string" === typeof b) return b;
  }
  return null;
}
function Sa(a) {
  switch (typeof a) {
    case "boolean":
    case "number":
    case "string":
    case "undefined":
      return a;
    case "object":
      return a;
    default:
      return "";
  }
}
function Ta(a) {
  var b = a.type;
  return (a = a.nodeName) && "input" === a.toLowerCase() && ("checkbox" === b || "radio" === b);
}
function Ua(a) {
  var b = Ta(a) ? "checked" : "value", c = Object.getOwnPropertyDescriptor(a.constructor.prototype, b), d = "" + a[b];
  if (!a.hasOwnProperty(b) && "undefined" !== typeof c && "function" === typeof c.get && "function" === typeof c.set) {
    var e = c.get, f2 = c.set;
    Object.defineProperty(a, b, { configurable: true, get: function() {
      return e.call(this);
    }, set: function(a2) {
      d = "" + a2;
      f2.call(this, a2);
    } });
    Object.defineProperty(a, b, { enumerable: c.enumerable });
    return { getValue: function() {
      return d;
    }, setValue: function(a2) {
      d = "" + a2;
    }, stopTracking: function() {
      a._valueTracker = null;
      delete a[b];
    } };
  }
}
function Va(a) {
  a._valueTracker || (a._valueTracker = Ua(a));
}
function Wa(a) {
  if (!a) return false;
  var b = a._valueTracker;
  if (!b) return true;
  var c = b.getValue();
  var d = "";
  a && (d = Ta(a) ? a.checked ? "true" : "false" : a.value);
  a = d;
  return a !== c ? (b.setValue(a), true) : false;
}
function Xa(a) {
  a = a || ("undefined" !== typeof document ? document : void 0);
  if ("undefined" === typeof a) return null;
  try {
    return a.activeElement || a.body;
  } catch (b) {
    return a.body;
  }
}
function Ya(a, b) {
  var c = b.checked;
  return A({}, b, { defaultChecked: void 0, defaultValue: void 0, value: void 0, checked: null != c ? c : a._wrapperState.initialChecked });
}
function Za(a, b) {
  var c = null == b.defaultValue ? "" : b.defaultValue, d = null != b.checked ? b.checked : b.defaultChecked;
  c = Sa(null != b.value ? b.value : c);
  a._wrapperState = { initialChecked: d, initialValue: c, controlled: "checkbox" === b.type || "radio" === b.type ? null != b.checked : null != b.value };
}
function ab(a, b) {
  b = b.checked;
  null != b && ta(a, "checked", b, false);
}
function bb(a, b) {
  ab(a, b);
  var c = Sa(b.value), d = b.type;
  if (null != c) if ("number" === d) {
    if (0 === c && "" === a.value || a.value != c) a.value = "" + c;
  } else a.value !== "" + c && (a.value = "" + c);
  else if ("submit" === d || "reset" === d) {
    a.removeAttribute("value");
    return;
  }
  b.hasOwnProperty("value") ? cb(a, b.type, c) : b.hasOwnProperty("defaultValue") && cb(a, b.type, Sa(b.defaultValue));
  null == b.checked && null != b.defaultChecked && (a.defaultChecked = !!b.defaultChecked);
}
function db(a, b, c) {
  if (b.hasOwnProperty("value") || b.hasOwnProperty("defaultValue")) {
    var d = b.type;
    if (!("submit" !== d && "reset" !== d || void 0 !== b.value && null !== b.value)) return;
    b = "" + a._wrapperState.initialValue;
    c || b === a.value || (a.value = b);
    a.defaultValue = b;
  }
  c = a.name;
  "" !== c && (a.name = "");
  a.defaultChecked = !!a._wrapperState.initialChecked;
  "" !== c && (a.name = c);
}
function cb(a, b, c) {
  if ("number" !== b || Xa(a.ownerDocument) !== a) null == c ? a.defaultValue = "" + a._wrapperState.initialValue : a.defaultValue !== "" + c && (a.defaultValue = "" + c);
}
var eb = Array.isArray;
function fb(a, b, c, d) {
  a = a.options;
  if (b) {
    b = {};
    for (var e = 0; e < c.length; e++) b["$" + c[e]] = true;
    for (c = 0; c < a.length; c++) e = b.hasOwnProperty("$" + a[c].value), a[c].selected !== e && (a[c].selected = e), e && d && (a[c].defaultSelected = true);
  } else {
    c = "" + Sa(c);
    b = null;
    for (e = 0; e < a.length; e++) {
      if (a[e].value === c) {
        a[e].selected = true;
        d && (a[e].defaultSelected = true);
        return;
      }
      null !== b || a[e].disabled || (b = a[e]);
    }
    null !== b && (b.selected = true);
  }
}
function gb(a, b) {
  if (null != b.dangerouslySetInnerHTML) throw Error(p(91));
  return A({}, b, { value: void 0, defaultValue: void 0, children: "" + a._wrapperState.initialValue });
}
function hb(a, b) {
  var c = b.value;
  if (null == c) {
    c = b.children;
    b = b.defaultValue;
    if (null != c) {
      if (null != b) throw Error(p(92));
      if (eb(c)) {
        if (1 < c.length) throw Error(p(93));
        c = c[0];
      }
      b = c;
    }
    null == b && (b = "");
    c = b;
  }
  a._wrapperState = { initialValue: Sa(c) };
}
function ib(a, b) {
  var c = Sa(b.value), d = Sa(b.defaultValue);
  null != c && (c = "" + c, c !== a.value && (a.value = c), null == b.defaultValue && a.defaultValue !== c && (a.defaultValue = c));
  null != d && (a.defaultValue = "" + d);
}
function jb(a) {
  var b = a.textContent;
  b === a._wrapperState.initialValue && "" !== b && null !== b && (a.value = b);
}
function kb(a) {
  switch (a) {
    case "svg":
      return "http://www.w3.org/2000/svg";
    case "math":
      return "http://www.w3.org/1998/Math/MathML";
    default:
      return "http://www.w3.org/1999/xhtml";
  }
}
function lb(a, b) {
  return null == a || "http://www.w3.org/1999/xhtml" === a ? kb(b) : "http://www.w3.org/2000/svg" === a && "foreignObject" === b ? "http://www.w3.org/1999/xhtml" : a;
}
var mb, nb = function(a) {
  return "undefined" !== typeof MSApp && MSApp.execUnsafeLocalFunction ? function(b, c, d, e) {
    MSApp.execUnsafeLocalFunction(function() {
      return a(b, c, d, e);
    });
  } : a;
}(function(a, b) {
  if ("http://www.w3.org/2000/svg" !== a.namespaceURI || "innerHTML" in a) a.innerHTML = b;
  else {
    mb = mb || document.createElement("div");
    mb.innerHTML = "<svg>" + b.valueOf().toString() + "</svg>";
    for (b = mb.firstChild; a.firstChild; ) a.removeChild(a.firstChild);
    for (; b.firstChild; ) a.appendChild(b.firstChild);
  }
});
function ob(a, b) {
  if (b) {
    var c = a.firstChild;
    if (c && c === a.lastChild && 3 === c.nodeType) {
      c.nodeValue = b;
      return;
    }
  }
  a.textContent = b;
}
var pb = {
  animationIterationCount: true,
  aspectRatio: true,
  borderImageOutset: true,
  borderImageSlice: true,
  borderImageWidth: true,
  boxFlex: true,
  boxFlexGroup: true,
  boxOrdinalGroup: true,
  columnCount: true,
  columns: true,
  flex: true,
  flexGrow: true,
  flexPositive: true,
  flexShrink: true,
  flexNegative: true,
  flexOrder: true,
  gridArea: true,
  gridRow: true,
  gridRowEnd: true,
  gridRowSpan: true,
  gridRowStart: true,
  gridColumn: true,
  gridColumnEnd: true,
  gridColumnSpan: true,
  gridColumnStart: true,
  fontWeight: true,
  lineClamp: true,
  lineHeight: true,
  opacity: true,
  order: true,
  orphans: true,
  tabSize: true,
  widows: true,
  zIndex: true,
  zoom: true,
  fillOpacity: true,
  floodOpacity: true,
  stopOpacity: true,
  strokeDasharray: true,
  strokeDashoffset: true,
  strokeMiterlimit: true,
  strokeOpacity: true,
  strokeWidth: true
}, qb = ["Webkit", "ms", "Moz", "O"];
Object.keys(pb).forEach(function(a) {
  qb.forEach(function(b) {
    b = b + a.charAt(0).toUpperCase() + a.substring(1);
    pb[b] = pb[a];
  });
});
function rb(a, b, c) {
  return null == b || "boolean" === typeof b || "" === b ? "" : c || "number" !== typeof b || 0 === b || pb.hasOwnProperty(a) && pb[a] ? ("" + b).trim() : b + "px";
}
function sb(a, b) {
  a = a.style;
  for (var c in b) if (b.hasOwnProperty(c)) {
    var d = 0 === c.indexOf("--"), e = rb(c, b[c], d);
    "float" === c && (c = "cssFloat");
    d ? a.setProperty(c, e) : a[c] = e;
  }
}
var tb = A({ menuitem: true }, { area: true, base: true, br: true, col: true, embed: true, hr: true, img: true, input: true, keygen: true, link: true, meta: true, param: true, source: true, track: true, wbr: true });
function ub(a, b) {
  if (b) {
    if (tb[a] && (null != b.children || null != b.dangerouslySetInnerHTML)) throw Error(p(137, a));
    if (null != b.dangerouslySetInnerHTML) {
      if (null != b.children) throw Error(p(60));
      if ("object" !== typeof b.dangerouslySetInnerHTML || !("__html" in b.dangerouslySetInnerHTML)) throw Error(p(61));
    }
    if (null != b.style && "object" !== typeof b.style) throw Error(p(62));
  }
}
function vb(a, b) {
  if (-1 === a.indexOf("-")) return "string" === typeof b.is;
  switch (a) {
    case "annotation-xml":
    case "color-profile":
    case "font-face":
    case "font-face-src":
    case "font-face-uri":
    case "font-face-format":
    case "font-face-name":
    case "missing-glyph":
      return false;
    default:
      return true;
  }
}
var wb = null;
function xb(a) {
  a = a.target || a.srcElement || window;
  a.correspondingUseElement && (a = a.correspondingUseElement);
  return 3 === a.nodeType ? a.parentNode : a;
}
var yb = null, zb = null, Ab = null;
function Bb(a) {
  if (a = Cb(a)) {
    if ("function" !== typeof yb) throw Error(p(280));
    var b = a.stateNode;
    b && (b = Db(b), yb(a.stateNode, a.type, b));
  }
}
function Eb(a) {
  zb ? Ab ? Ab.push(a) : Ab = [a] : zb = a;
}
function Fb() {
  if (zb) {
    var a = zb, b = Ab;
    Ab = zb = null;
    Bb(a);
    if (b) for (a = 0; a < b.length; a++) Bb(b[a]);
  }
}
function Gb(a, b) {
  return a(b);
}
function Hb() {
}
var Ib = false;
function Jb(a, b, c) {
  if (Ib) return a(b, c);
  Ib = true;
  try {
    return Gb(a, b, c);
  } finally {
    if (Ib = false, null !== zb || null !== Ab) Hb(), Fb();
  }
}
function Kb(a, b) {
  var c = a.stateNode;
  if (null === c) return null;
  var d = Db(c);
  if (null === d) return null;
  c = d[b];
  a: switch (b) {
    case "onClick":
    case "onClickCapture":
    case "onDoubleClick":
    case "onDoubleClickCapture":
    case "onMouseDown":
    case "onMouseDownCapture":
    case "onMouseMove":
    case "onMouseMoveCapture":
    case "onMouseUp":
    case "onMouseUpCapture":
    case "onMouseEnter":
      (d = !d.disabled) || (a = a.type, d = !("button" === a || "input" === a || "select" === a || "textarea" === a));
      a = !d;
      break a;
    default:
      a = false;
  }
  if (a) return null;
  if (c && "function" !== typeof c) throw Error(p(231, b, typeof c));
  return c;
}
var Lb = false;
if (ia) try {
  var Mb = {};
  Object.defineProperty(Mb, "passive", { get: function() {
    Lb = true;
  } });
  window.addEventListener("test", Mb, Mb);
  window.removeEventListener("test", Mb, Mb);
} catch (a) {
  Lb = false;
}
function Nb(a, b, c, d, e, f2, g, h, k2) {
  var l2 = Array.prototype.slice.call(arguments, 3);
  try {
    b.apply(c, l2);
  } catch (m2) {
    this.onError(m2);
  }
}
var Ob = false, Pb = null, Qb = false, Rb = null, Sb = { onError: function(a) {
  Ob = true;
  Pb = a;
} };
function Tb(a, b, c, d, e, f2, g, h, k2) {
  Ob = false;
  Pb = null;
  Nb.apply(Sb, arguments);
}
function Ub(a, b, c, d, e, f2, g, h, k2) {
  Tb.apply(this, arguments);
  if (Ob) {
    if (Ob) {
      var l2 = Pb;
      Ob = false;
      Pb = null;
    } else throw Error(p(198));
    Qb || (Qb = true, Rb = l2);
  }
}
function Vb(a) {
  var b = a, c = a;
  if (a.alternate) for (; b.return; ) b = b.return;
  else {
    a = b;
    do
      b = a, 0 !== (b.flags & 4098) && (c = b.return), a = b.return;
    while (a);
  }
  return 3 === b.tag ? c : null;
}
function Wb(a) {
  if (13 === a.tag) {
    var b = a.memoizedState;
    null === b && (a = a.alternate, null !== a && (b = a.memoizedState));
    if (null !== b) return b.dehydrated;
  }
  return null;
}
function Xb(a) {
  if (Vb(a) !== a) throw Error(p(188));
}
function Yb(a) {
  var b = a.alternate;
  if (!b) {
    b = Vb(a);
    if (null === b) throw Error(p(188));
    return b !== a ? null : a;
  }
  for (var c = a, d = b; ; ) {
    var e = c.return;
    if (null === e) break;
    var f2 = e.alternate;
    if (null === f2) {
      d = e.return;
      if (null !== d) {
        c = d;
        continue;
      }
      break;
    }
    if (e.child === f2.child) {
      for (f2 = e.child; f2; ) {
        if (f2 === c) return Xb(e), a;
        if (f2 === d) return Xb(e), b;
        f2 = f2.sibling;
      }
      throw Error(p(188));
    }
    if (c.return !== d.return) c = e, d = f2;
    else {
      for (var g = false, h = e.child; h; ) {
        if (h === c) {
          g = true;
          c = e;
          d = f2;
          break;
        }
        if (h === d) {
          g = true;
          d = e;
          c = f2;
          break;
        }
        h = h.sibling;
      }
      if (!g) {
        for (h = f2.child; h; ) {
          if (h === c) {
            g = true;
            c = f2;
            d = e;
            break;
          }
          if (h === d) {
            g = true;
            d = f2;
            c = e;
            break;
          }
          h = h.sibling;
        }
        if (!g) throw Error(p(189));
      }
    }
    if (c.alternate !== d) throw Error(p(190));
  }
  if (3 !== c.tag) throw Error(p(188));
  return c.stateNode.current === c ? a : b;
}
function Zb(a) {
  a = Yb(a);
  return null !== a ? $b(a) : null;
}
function $b(a) {
  if (5 === a.tag || 6 === a.tag) return a;
  for (a = a.child; null !== a; ) {
    var b = $b(a);
    if (null !== b) return b;
    a = a.sibling;
  }
  return null;
}
var ac = ca.unstable_scheduleCallback, bc = ca.unstable_cancelCallback, cc = ca.unstable_shouldYield, dc = ca.unstable_requestPaint, B = ca.unstable_now, ec = ca.unstable_getCurrentPriorityLevel, fc = ca.unstable_ImmediatePriority, gc = ca.unstable_UserBlockingPriority, hc = ca.unstable_NormalPriority, ic = ca.unstable_LowPriority, jc = ca.unstable_IdlePriority, kc = null, lc = null;
function mc(a) {
  if (lc && "function" === typeof lc.onCommitFiberRoot) try {
    lc.onCommitFiberRoot(kc, a, void 0, 128 === (a.current.flags & 128));
  } catch (b) {
  }
}
var oc = Math.clz32 ? Math.clz32 : nc, pc = Math.log, qc = Math.LN2;
function nc(a) {
  a >>>= 0;
  return 0 === a ? 32 : 31 - (pc(a) / qc | 0) | 0;
}
var rc = 64, sc = 4194304;
function tc(a) {
  switch (a & -a) {
    case 1:
      return 1;
    case 2:
      return 2;
    case 4:
      return 4;
    case 8:
      return 8;
    case 16:
      return 16;
    case 32:
      return 32;
    case 64:
    case 128:
    case 256:
    case 512:
    case 1024:
    case 2048:
    case 4096:
    case 8192:
    case 16384:
    case 32768:
    case 65536:
    case 131072:
    case 262144:
    case 524288:
    case 1048576:
    case 2097152:
      return a & 4194240;
    case 4194304:
    case 8388608:
    case 16777216:
    case 33554432:
    case 67108864:
      return a & 130023424;
    case 134217728:
      return 134217728;
    case 268435456:
      return 268435456;
    case 536870912:
      return 536870912;
    case 1073741824:
      return 1073741824;
    default:
      return a;
  }
}
function uc(a, b) {
  var c = a.pendingLanes;
  if (0 === c) return 0;
  var d = 0, e = a.suspendedLanes, f2 = a.pingedLanes, g = c & 268435455;
  if (0 !== g) {
    var h = g & ~e;
    0 !== h ? d = tc(h) : (f2 &= g, 0 !== f2 && (d = tc(f2)));
  } else g = c & ~e, 0 !== g ? d = tc(g) : 0 !== f2 && (d = tc(f2));
  if (0 === d) return 0;
  if (0 !== b && b !== d && 0 === (b & e) && (e = d & -d, f2 = b & -b, e >= f2 || 16 === e && 0 !== (f2 & 4194240))) return b;
  0 !== (d & 4) && (d |= c & 16);
  b = a.entangledLanes;
  if (0 !== b) for (a = a.entanglements, b &= d; 0 < b; ) c = 31 - oc(b), e = 1 << c, d |= a[c], b &= ~e;
  return d;
}
function vc(a, b) {
  switch (a) {
    case 1:
    case 2:
    case 4:
      return b + 250;
    case 8:
    case 16:
    case 32:
    case 64:
    case 128:
    case 256:
    case 512:
    case 1024:
    case 2048:
    case 4096:
    case 8192:
    case 16384:
    case 32768:
    case 65536:
    case 131072:
    case 262144:
    case 524288:
    case 1048576:
    case 2097152:
      return b + 5e3;
    case 4194304:
    case 8388608:
    case 16777216:
    case 33554432:
    case 67108864:
      return -1;
    case 134217728:
    case 268435456:
    case 536870912:
    case 1073741824:
      return -1;
    default:
      return -1;
  }
}
function wc(a, b) {
  for (var c = a.suspendedLanes, d = a.pingedLanes, e = a.expirationTimes, f2 = a.pendingLanes; 0 < f2; ) {
    var g = 31 - oc(f2), h = 1 << g, k2 = e[g];
    if (-1 === k2) {
      if (0 === (h & c) || 0 !== (h & d)) e[g] = vc(h, b);
    } else k2 <= b && (a.expiredLanes |= h);
    f2 &= ~h;
  }
}
function xc(a) {
  a = a.pendingLanes & -1073741825;
  return 0 !== a ? a : a & 1073741824 ? 1073741824 : 0;
}
function yc() {
  var a = rc;
  rc <<= 1;
  0 === (rc & 4194240) && (rc = 64);
  return a;
}
function zc(a) {
  for (var b = [], c = 0; 31 > c; c++) b.push(a);
  return b;
}
function Ac(a, b, c) {
  a.pendingLanes |= b;
  536870912 !== b && (a.suspendedLanes = 0, a.pingedLanes = 0);
  a = a.eventTimes;
  b = 31 - oc(b);
  a[b] = c;
}
function Bc(a, b) {
  var c = a.pendingLanes & ~b;
  a.pendingLanes = b;
  a.suspendedLanes = 0;
  a.pingedLanes = 0;
  a.expiredLanes &= b;
  a.mutableReadLanes &= b;
  a.entangledLanes &= b;
  b = a.entanglements;
  var d = a.eventTimes;
  for (a = a.expirationTimes; 0 < c; ) {
    var e = 31 - oc(c), f2 = 1 << e;
    b[e] = 0;
    d[e] = -1;
    a[e] = -1;
    c &= ~f2;
  }
}
function Cc(a, b) {
  var c = a.entangledLanes |= b;
  for (a = a.entanglements; c; ) {
    var d = 31 - oc(c), e = 1 << d;
    e & b | a[d] & b && (a[d] |= b);
    c &= ~e;
  }
}
var C = 0;
function Dc(a) {
  a &= -a;
  return 1 < a ? 4 < a ? 0 !== (a & 268435455) ? 16 : 536870912 : 4 : 1;
}
var Ec, Fc, Gc, Hc, Ic, Jc = false, Kc = [], Lc = null, Mc = null, Nc = null, Oc = /* @__PURE__ */ new Map(), Pc = /* @__PURE__ */ new Map(), Qc = [], Rc = "mousedown mouseup touchcancel touchend touchstart auxclick dblclick pointercancel pointerdown pointerup dragend dragstart drop compositionend compositionstart keydown keypress keyup input textInput copy cut paste click change contextmenu reset submit".split(" ");
function Sc(a, b) {
  switch (a) {
    case "focusin":
    case "focusout":
      Lc = null;
      break;
    case "dragenter":
    case "dragleave":
      Mc = null;
      break;
    case "mouseover":
    case "mouseout":
      Nc = null;
      break;
    case "pointerover":
    case "pointerout":
      Oc.delete(b.pointerId);
      break;
    case "gotpointercapture":
    case "lostpointercapture":
      Pc.delete(b.pointerId);
  }
}
function Tc(a, b, c, d, e, f2) {
  if (null === a || a.nativeEvent !== f2) return a = { blockedOn: b, domEventName: c, eventSystemFlags: d, nativeEvent: f2, targetContainers: [e] }, null !== b && (b = Cb(b), null !== b && Fc(b)), a;
  a.eventSystemFlags |= d;
  b = a.targetContainers;
  null !== e && -1 === b.indexOf(e) && b.push(e);
  return a;
}
function Uc(a, b, c, d, e) {
  switch (b) {
    case "focusin":
      return Lc = Tc(Lc, a, b, c, d, e), true;
    case "dragenter":
      return Mc = Tc(Mc, a, b, c, d, e), true;
    case "mouseover":
      return Nc = Tc(Nc, a, b, c, d, e), true;
    case "pointerover":
      var f2 = e.pointerId;
      Oc.set(f2, Tc(Oc.get(f2) || null, a, b, c, d, e));
      return true;
    case "gotpointercapture":
      return f2 = e.pointerId, Pc.set(f2, Tc(Pc.get(f2) || null, a, b, c, d, e)), true;
  }
  return false;
}
function Vc(a) {
  var b = Wc(a.target);
  if (null !== b) {
    var c = Vb(b);
    if (null !== c) {
      if (b = c.tag, 13 === b) {
        if (b = Wb(c), null !== b) {
          a.blockedOn = b;
          Ic(a.priority, function() {
            Gc(c);
          });
          return;
        }
      } else if (3 === b && c.stateNode.current.memoizedState.isDehydrated) {
        a.blockedOn = 3 === c.tag ? c.stateNode.containerInfo : null;
        return;
      }
    }
  }
  a.blockedOn = null;
}
function Xc(a) {
  if (null !== a.blockedOn) return false;
  for (var b = a.targetContainers; 0 < b.length; ) {
    var c = Yc(a.domEventName, a.eventSystemFlags, b[0], a.nativeEvent);
    if (null === c) {
      c = a.nativeEvent;
      var d = new c.constructor(c.type, c);
      wb = d;
      c.target.dispatchEvent(d);
      wb = null;
    } else return b = Cb(c), null !== b && Fc(b), a.blockedOn = c, false;
    b.shift();
  }
  return true;
}
function Zc(a, b, c) {
  Xc(a) && c.delete(b);
}
function $c() {
  Jc = false;
  null !== Lc && Xc(Lc) && (Lc = null);
  null !== Mc && Xc(Mc) && (Mc = null);
  null !== Nc && Xc(Nc) && (Nc = null);
  Oc.forEach(Zc);
  Pc.forEach(Zc);
}
function ad(a, b) {
  a.blockedOn === b && (a.blockedOn = null, Jc || (Jc = true, ca.unstable_scheduleCallback(ca.unstable_NormalPriority, $c)));
}
function bd(a) {
  function b(b2) {
    return ad(b2, a);
  }
  if (0 < Kc.length) {
    ad(Kc[0], a);
    for (var c = 1; c < Kc.length; c++) {
      var d = Kc[c];
      d.blockedOn === a && (d.blockedOn = null);
    }
  }
  null !== Lc && ad(Lc, a);
  null !== Mc && ad(Mc, a);
  null !== Nc && ad(Nc, a);
  Oc.forEach(b);
  Pc.forEach(b);
  for (c = 0; c < Qc.length; c++) d = Qc[c], d.blockedOn === a && (d.blockedOn = null);
  for (; 0 < Qc.length && (c = Qc[0], null === c.blockedOn); ) Vc(c), null === c.blockedOn && Qc.shift();
}
var cd = ua.ReactCurrentBatchConfig, dd = true;
function ed(a, b, c, d) {
  var e = C, f2 = cd.transition;
  cd.transition = null;
  try {
    C = 1, fd(a, b, c, d);
  } finally {
    C = e, cd.transition = f2;
  }
}
function gd(a, b, c, d) {
  var e = C, f2 = cd.transition;
  cd.transition = null;
  try {
    C = 4, fd(a, b, c, d);
  } finally {
    C = e, cd.transition = f2;
  }
}
function fd(a, b, c, d) {
  if (dd) {
    var e = Yc(a, b, c, d);
    if (null === e) hd(a, b, d, id, c), Sc(a, d);
    else if (Uc(e, a, b, c, d)) d.stopPropagation();
    else if (Sc(a, d), b & 4 && -1 < Rc.indexOf(a)) {
      for (; null !== e; ) {
        var f2 = Cb(e);
        null !== f2 && Ec(f2);
        f2 = Yc(a, b, c, d);
        null === f2 && hd(a, b, d, id, c);
        if (f2 === e) break;
        e = f2;
      }
      null !== e && d.stopPropagation();
    } else hd(a, b, d, null, c);
  }
}
var id = null;
function Yc(a, b, c, d) {
  id = null;
  a = xb(d);
  a = Wc(a);
  if (null !== a) if (b = Vb(a), null === b) a = null;
  else if (c = b.tag, 13 === c) {
    a = Wb(b);
    if (null !== a) return a;
    a = null;
  } else if (3 === c) {
    if (b.stateNode.current.memoizedState.isDehydrated) return 3 === b.tag ? b.stateNode.containerInfo : null;
    a = null;
  } else b !== a && (a = null);
  id = a;
  return null;
}
function jd(a) {
  switch (a) {
    case "cancel":
    case "click":
    case "close":
    case "contextmenu":
    case "copy":
    case "cut":
    case "auxclick":
    case "dblclick":
    case "dragend":
    case "dragstart":
    case "drop":
    case "focusin":
    case "focusout":
    case "input":
    case "invalid":
    case "keydown":
    case "keypress":
    case "keyup":
    case "mousedown":
    case "mouseup":
    case "paste":
    case "pause":
    case "play":
    case "pointercancel":
    case "pointerdown":
    case "pointerup":
    case "ratechange":
    case "reset":
    case "resize":
    case "seeked":
    case "submit":
    case "touchcancel":
    case "touchend":
    case "touchstart":
    case "volumechange":
    case "change":
    case "selectionchange":
    case "textInput":
    case "compositionstart":
    case "compositionend":
    case "compositionupdate":
    case "beforeblur":
    case "afterblur":
    case "beforeinput":
    case "blur":
    case "fullscreenchange":
    case "focus":
    case "hashchange":
    case "popstate":
    case "select":
    case "selectstart":
      return 1;
    case "drag":
    case "dragenter":
    case "dragexit":
    case "dragleave":
    case "dragover":
    case "mousemove":
    case "mouseout":
    case "mouseover":
    case "pointermove":
    case "pointerout":
    case "pointerover":
    case "scroll":
    case "toggle":
    case "touchmove":
    case "wheel":
    case "mouseenter":
    case "mouseleave":
    case "pointerenter":
    case "pointerleave":
      return 4;
    case "message":
      switch (ec()) {
        case fc:
          return 1;
        case gc:
          return 4;
        case hc:
        case ic:
          return 16;
        case jc:
          return 536870912;
        default:
          return 16;
      }
    default:
      return 16;
  }
}
var kd = null, ld = null, md = null;
function nd() {
  if (md) return md;
  var a, b = ld, c = b.length, d, e = "value" in kd ? kd.value : kd.textContent, f2 = e.length;
  for (a = 0; a < c && b[a] === e[a]; a++) ;
  var g = c - a;
  for (d = 1; d <= g && b[c - d] === e[f2 - d]; d++) ;
  return md = e.slice(a, 1 < d ? 1 - d : void 0);
}
function od(a) {
  var b = a.keyCode;
  "charCode" in a ? (a = a.charCode, 0 === a && 13 === b && (a = 13)) : a = b;
  10 === a && (a = 13);
  return 32 <= a || 13 === a ? a : 0;
}
function pd() {
  return true;
}
function qd() {
  return false;
}
function rd(a) {
  function b(b2, d, e, f2, g) {
    this._reactName = b2;
    this._targetInst = e;
    this.type = d;
    this.nativeEvent = f2;
    this.target = g;
    this.currentTarget = null;
    for (var c in a) a.hasOwnProperty(c) && (b2 = a[c], this[c] = b2 ? b2(f2) : f2[c]);
    this.isDefaultPrevented = (null != f2.defaultPrevented ? f2.defaultPrevented : false === f2.returnValue) ? pd : qd;
    this.isPropagationStopped = qd;
    return this;
  }
  A(b.prototype, { preventDefault: function() {
    this.defaultPrevented = true;
    var a2 = this.nativeEvent;
    a2 && (a2.preventDefault ? a2.preventDefault() : "unknown" !== typeof a2.returnValue && (a2.returnValue = false), this.isDefaultPrevented = pd);
  }, stopPropagation: function() {
    var a2 = this.nativeEvent;
    a2 && (a2.stopPropagation ? a2.stopPropagation() : "unknown" !== typeof a2.cancelBubble && (a2.cancelBubble = true), this.isPropagationStopped = pd);
  }, persist: function() {
  }, isPersistent: pd });
  return b;
}
var sd = { eventPhase: 0, bubbles: 0, cancelable: 0, timeStamp: function(a) {
  return a.timeStamp || Date.now();
}, defaultPrevented: 0, isTrusted: 0 }, td = rd(sd), ud = A({}, sd, { view: 0, detail: 0 }), vd = rd(ud), wd, xd, yd, Ad = A({}, ud, { screenX: 0, screenY: 0, clientX: 0, clientY: 0, pageX: 0, pageY: 0, ctrlKey: 0, shiftKey: 0, altKey: 0, metaKey: 0, getModifierState: zd, button: 0, buttons: 0, relatedTarget: function(a) {
  return void 0 === a.relatedTarget ? a.fromElement === a.srcElement ? a.toElement : a.fromElement : a.relatedTarget;
}, movementX: function(a) {
  if ("movementX" in a) return a.movementX;
  a !== yd && (yd && "mousemove" === a.type ? (wd = a.screenX - yd.screenX, xd = a.screenY - yd.screenY) : xd = wd = 0, yd = a);
  return wd;
}, movementY: function(a) {
  return "movementY" in a ? a.movementY : xd;
} }), Bd = rd(Ad), Cd = A({}, Ad, { dataTransfer: 0 }), Dd = rd(Cd), Ed = A({}, ud, { relatedTarget: 0 }), Fd = rd(Ed), Gd = A({}, sd, { animationName: 0, elapsedTime: 0, pseudoElement: 0 }), Hd = rd(Gd), Id = A({}, sd, { clipboardData: function(a) {
  return "clipboardData" in a ? a.clipboardData : window.clipboardData;
} }), Jd = rd(Id), Kd = A({}, sd, { data: 0 }), Ld = rd(Kd), Md = {
  Esc: "Escape",
  Spacebar: " ",
  Left: "ArrowLeft",
  Up: "ArrowUp",
  Right: "ArrowRight",
  Down: "ArrowDown",
  Del: "Delete",
  Win: "OS",
  Menu: "ContextMenu",
  Apps: "ContextMenu",
  Scroll: "ScrollLock",
  MozPrintableKey: "Unidentified"
}, Nd = {
  8: "Backspace",
  9: "Tab",
  12: "Clear",
  13: "Enter",
  16: "Shift",
  17: "Control",
  18: "Alt",
  19: "Pause",
  20: "CapsLock",
  27: "Escape",
  32: " ",
  33: "PageUp",
  34: "PageDown",
  35: "End",
  36: "Home",
  37: "ArrowLeft",
  38: "ArrowUp",
  39: "ArrowRight",
  40: "ArrowDown",
  45: "Insert",
  46: "Delete",
  112: "F1",
  113: "F2",
  114: "F3",
  115: "F4",
  116: "F5",
  117: "F6",
  118: "F7",
  119: "F8",
  120: "F9",
  121: "F10",
  122: "F11",
  123: "F12",
  144: "NumLock",
  145: "ScrollLock",
  224: "Meta"
}, Od = { Alt: "altKey", Control: "ctrlKey", Meta: "metaKey", Shift: "shiftKey" };
function Pd(a) {
  var b = this.nativeEvent;
  return b.getModifierState ? b.getModifierState(a) : (a = Od[a]) ? !!b[a] : false;
}
function zd() {
  return Pd;
}
var Qd = A({}, ud, { key: function(a) {
  if (a.key) {
    var b = Md[a.key] || a.key;
    if ("Unidentified" !== b) return b;
  }
  return "keypress" === a.type ? (a = od(a), 13 === a ? "Enter" : String.fromCharCode(a)) : "keydown" === a.type || "keyup" === a.type ? Nd[a.keyCode] || "Unidentified" : "";
}, code: 0, location: 0, ctrlKey: 0, shiftKey: 0, altKey: 0, metaKey: 0, repeat: 0, locale: 0, getModifierState: zd, charCode: function(a) {
  return "keypress" === a.type ? od(a) : 0;
}, keyCode: function(a) {
  return "keydown" === a.type || "keyup" === a.type ? a.keyCode : 0;
}, which: function(a) {
  return "keypress" === a.type ? od(a) : "keydown" === a.type || "keyup" === a.type ? a.keyCode : 0;
} }), Rd = rd(Qd), Sd = A({}, Ad, { pointerId: 0, width: 0, height: 0, pressure: 0, tangentialPressure: 0, tiltX: 0, tiltY: 0, twist: 0, pointerType: 0, isPrimary: 0 }), Td = rd(Sd), Ud = A({}, ud, { touches: 0, targetTouches: 0, changedTouches: 0, altKey: 0, metaKey: 0, ctrlKey: 0, shiftKey: 0, getModifierState: zd }), Vd = rd(Ud), Wd = A({}, sd, { propertyName: 0, elapsedTime: 0, pseudoElement: 0 }), Xd = rd(Wd), Yd = A({}, Ad, {
  deltaX: function(a) {
    return "deltaX" in a ? a.deltaX : "wheelDeltaX" in a ? -a.wheelDeltaX : 0;
  },
  deltaY: function(a) {
    return "deltaY" in a ? a.deltaY : "wheelDeltaY" in a ? -a.wheelDeltaY : "wheelDelta" in a ? -a.wheelDelta : 0;
  },
  deltaZ: 0,
  deltaMode: 0
}), Zd = rd(Yd), $d = [9, 13, 27, 32], ae = ia && "CompositionEvent" in window, be = null;
ia && "documentMode" in document && (be = document.documentMode);
var ce = ia && "TextEvent" in window && !be, de = ia && (!ae || be && 8 < be && 11 >= be), ee = String.fromCharCode(32), fe = false;
function ge(a, b) {
  switch (a) {
    case "keyup":
      return -1 !== $d.indexOf(b.keyCode);
    case "keydown":
      return 229 !== b.keyCode;
    case "keypress":
    case "mousedown":
    case "focusout":
      return true;
    default:
      return false;
  }
}
function he(a) {
  a = a.detail;
  return "object" === typeof a && "data" in a ? a.data : null;
}
var ie = false;
function je(a, b) {
  switch (a) {
    case "compositionend":
      return he(b);
    case "keypress":
      if (32 !== b.which) return null;
      fe = true;
      return ee;
    case "textInput":
      return a = b.data, a === ee && fe ? null : a;
    default:
      return null;
  }
}
function ke(a, b) {
  if (ie) return "compositionend" === a || !ae && ge(a, b) ? (a = nd(), md = ld = kd = null, ie = false, a) : null;
  switch (a) {
    case "paste":
      return null;
    case "keypress":
      if (!(b.ctrlKey || b.altKey || b.metaKey) || b.ctrlKey && b.altKey) {
        if (b.char && 1 < b.char.length) return b.char;
        if (b.which) return String.fromCharCode(b.which);
      }
      return null;
    case "compositionend":
      return de && "ko" !== b.locale ? null : b.data;
    default:
      return null;
  }
}
var le = { color: true, date: true, datetime: true, "datetime-local": true, email: true, month: true, number: true, password: true, range: true, search: true, tel: true, text: true, time: true, url: true, week: true };
function me(a) {
  var b = a && a.nodeName && a.nodeName.toLowerCase();
  return "input" === b ? !!le[a.type] : "textarea" === b ? true : false;
}
function ne(a, b, c, d) {
  Eb(d);
  b = oe(b, "onChange");
  0 < b.length && (c = new td("onChange", "change", null, c, d), a.push({ event: c, listeners: b }));
}
var pe = null, qe = null;
function re(a) {
  se(a, 0);
}
function te(a) {
  var b = ue(a);
  if (Wa(b)) return a;
}
function ve(a, b) {
  if ("change" === a) return b;
}
var we = false;
if (ia) {
  var xe;
  if (ia) {
    var ye = "oninput" in document;
    if (!ye) {
      var ze = document.createElement("div");
      ze.setAttribute("oninput", "return;");
      ye = "function" === typeof ze.oninput;
    }
    xe = ye;
  } else xe = false;
  we = xe && (!document.documentMode || 9 < document.documentMode);
}
function Ae() {
  pe && (pe.detachEvent("onpropertychange", Be), qe = pe = null);
}
function Be(a) {
  if ("value" === a.propertyName && te(qe)) {
    var b = [];
    ne(b, qe, a, xb(a));
    Jb(re, b);
  }
}
function Ce(a, b, c) {
  "focusin" === a ? (Ae(), pe = b, qe = c, pe.attachEvent("onpropertychange", Be)) : "focusout" === a && Ae();
}
function De(a) {
  if ("selectionchange" === a || "keyup" === a || "keydown" === a) return te(qe);
}
function Ee(a, b) {
  if ("click" === a) return te(b);
}
function Fe(a, b) {
  if ("input" === a || "change" === a) return te(b);
}
function Ge(a, b) {
  return a === b && (0 !== a || 1 / a === 1 / b) || a !== a && b !== b;
}
var He = "function" === typeof Object.is ? Object.is : Ge;
function Ie(a, b) {
  if (He(a, b)) return true;
  if ("object" !== typeof a || null === a || "object" !== typeof b || null === b) return false;
  var c = Object.keys(a), d = Object.keys(b);
  if (c.length !== d.length) return false;
  for (d = 0; d < c.length; d++) {
    var e = c[d];
    if (!ja.call(b, e) || !He(a[e], b[e])) return false;
  }
  return true;
}
function Je(a) {
  for (; a && a.firstChild; ) a = a.firstChild;
  return a;
}
function Ke(a, b) {
  var c = Je(a);
  a = 0;
  for (var d; c; ) {
    if (3 === c.nodeType) {
      d = a + c.textContent.length;
      if (a <= b && d >= b) return { node: c, offset: b - a };
      a = d;
    }
    a: {
      for (; c; ) {
        if (c.nextSibling) {
          c = c.nextSibling;
          break a;
        }
        c = c.parentNode;
      }
      c = void 0;
    }
    c = Je(c);
  }
}
function Le(a, b) {
  return a && b ? a === b ? true : a && 3 === a.nodeType ? false : b && 3 === b.nodeType ? Le(a, b.parentNode) : "contains" in a ? a.contains(b) : a.compareDocumentPosition ? !!(a.compareDocumentPosition(b) & 16) : false : false;
}
function Me() {
  for (var a = window, b = Xa(); b instanceof a.HTMLIFrameElement; ) {
    try {
      var c = "string" === typeof b.contentWindow.location.href;
    } catch (d) {
      c = false;
    }
    if (c) a = b.contentWindow;
    else break;
    b = Xa(a.document);
  }
  return b;
}
function Ne(a) {
  var b = a && a.nodeName && a.nodeName.toLowerCase();
  return b && ("input" === b && ("text" === a.type || "search" === a.type || "tel" === a.type || "url" === a.type || "password" === a.type) || "textarea" === b || "true" === a.contentEditable);
}
function Oe(a) {
  var b = Me(), c = a.focusedElem, d = a.selectionRange;
  if (b !== c && c && c.ownerDocument && Le(c.ownerDocument.documentElement, c)) {
    if (null !== d && Ne(c)) {
      if (b = d.start, a = d.end, void 0 === a && (a = b), "selectionStart" in c) c.selectionStart = b, c.selectionEnd = Math.min(a, c.value.length);
      else if (a = (b = c.ownerDocument || document) && b.defaultView || window, a.getSelection) {
        a = a.getSelection();
        var e = c.textContent.length, f2 = Math.min(d.start, e);
        d = void 0 === d.end ? f2 : Math.min(d.end, e);
        !a.extend && f2 > d && (e = d, d = f2, f2 = e);
        e = Ke(c, f2);
        var g = Ke(
          c,
          d
        );
        e && g && (1 !== a.rangeCount || a.anchorNode !== e.node || a.anchorOffset !== e.offset || a.focusNode !== g.node || a.focusOffset !== g.offset) && (b = b.createRange(), b.setStart(e.node, e.offset), a.removeAllRanges(), f2 > d ? (a.addRange(b), a.extend(g.node, g.offset)) : (b.setEnd(g.node, g.offset), a.addRange(b)));
      }
    }
    b = [];
    for (a = c; a = a.parentNode; ) 1 === a.nodeType && b.push({ element: a, left: a.scrollLeft, top: a.scrollTop });
    "function" === typeof c.focus && c.focus();
    for (c = 0; c < b.length; c++) a = b[c], a.element.scrollLeft = a.left, a.element.scrollTop = a.top;
  }
}
var Pe = ia && "documentMode" in document && 11 >= document.documentMode, Qe = null, Re = null, Se = null, Te = false;
function Ue(a, b, c) {
  var d = c.window === c ? c.document : 9 === c.nodeType ? c : c.ownerDocument;
  Te || null == Qe || Qe !== Xa(d) || (d = Qe, "selectionStart" in d && Ne(d) ? d = { start: d.selectionStart, end: d.selectionEnd } : (d = (d.ownerDocument && d.ownerDocument.defaultView || window).getSelection(), d = { anchorNode: d.anchorNode, anchorOffset: d.anchorOffset, focusNode: d.focusNode, focusOffset: d.focusOffset }), Se && Ie(Se, d) || (Se = d, d = oe(Re, "onSelect"), 0 < d.length && (b = new td("onSelect", "select", null, b, c), a.push({ event: b, listeners: d }), b.target = Qe)));
}
function Ve(a, b) {
  var c = {};
  c[a.toLowerCase()] = b.toLowerCase();
  c["Webkit" + a] = "webkit" + b;
  c["Moz" + a] = "moz" + b;
  return c;
}
var We = { animationend: Ve("Animation", "AnimationEnd"), animationiteration: Ve("Animation", "AnimationIteration"), animationstart: Ve("Animation", "AnimationStart"), transitionend: Ve("Transition", "TransitionEnd") }, Xe = {}, Ye = {};
ia && (Ye = document.createElement("div").style, "AnimationEvent" in window || (delete We.animationend.animation, delete We.animationiteration.animation, delete We.animationstart.animation), "TransitionEvent" in window || delete We.transitionend.transition);
function Ze(a) {
  if (Xe[a]) return Xe[a];
  if (!We[a]) return a;
  var b = We[a], c;
  for (c in b) if (b.hasOwnProperty(c) && c in Ye) return Xe[a] = b[c];
  return a;
}
var $e = Ze("animationend"), af = Ze("animationiteration"), bf = Ze("animationstart"), cf = Ze("transitionend"), df = /* @__PURE__ */ new Map(), ef = "abort auxClick cancel canPlay canPlayThrough click close contextMenu copy cut drag dragEnd dragEnter dragExit dragLeave dragOver dragStart drop durationChange emptied encrypted ended error gotPointerCapture input invalid keyDown keyPress keyUp load loadedData loadedMetadata loadStart lostPointerCapture mouseDown mouseMove mouseOut mouseOver mouseUp paste pause play playing pointerCancel pointerDown pointerMove pointerOut pointerOver pointerUp progress rateChange reset resize seeked seeking stalled submit suspend timeUpdate touchCancel touchEnd touchStart volumeChange scroll toggle touchMove waiting wheel".split(" ");
function ff(a, b) {
  df.set(a, b);
  fa(b, [a]);
}
for (var gf = 0; gf < ef.length; gf++) {
  var hf = ef[gf], jf = hf.toLowerCase(), kf = hf[0].toUpperCase() + hf.slice(1);
  ff(jf, "on" + kf);
}
ff($e, "onAnimationEnd");
ff(af, "onAnimationIteration");
ff(bf, "onAnimationStart");
ff("dblclick", "onDoubleClick");
ff("focusin", "onFocus");
ff("focusout", "onBlur");
ff(cf, "onTransitionEnd");
ha("onMouseEnter", ["mouseout", "mouseover"]);
ha("onMouseLeave", ["mouseout", "mouseover"]);
ha("onPointerEnter", ["pointerout", "pointerover"]);
ha("onPointerLeave", ["pointerout", "pointerover"]);
fa("onChange", "change click focusin focusout input keydown keyup selectionchange".split(" "));
fa("onSelect", "focusout contextmenu dragend focusin keydown keyup mousedown mouseup selectionchange".split(" "));
fa("onBeforeInput", ["compositionend", "keypress", "textInput", "paste"]);
fa("onCompositionEnd", "compositionend focusout keydown keypress keyup mousedown".split(" "));
fa("onCompositionStart", "compositionstart focusout keydown keypress keyup mousedown".split(" "));
fa("onCompositionUpdate", "compositionupdate focusout keydown keypress keyup mousedown".split(" "));
var lf = "abort canplay canplaythrough durationchange emptied encrypted ended error loadeddata loadedmetadata loadstart pause play playing progress ratechange resize seeked seeking stalled suspend timeupdate volumechange waiting".split(" "), mf = new Set("cancel close invalid load scroll toggle".split(" ").concat(lf));
function nf(a, b, c) {
  var d = a.type || "unknown-event";
  a.currentTarget = c;
  Ub(d, b, void 0, a);
  a.currentTarget = null;
}
function se(a, b) {
  b = 0 !== (b & 4);
  for (var c = 0; c < a.length; c++) {
    var d = a[c], e = d.event;
    d = d.listeners;
    a: {
      var f2 = void 0;
      if (b) for (var g = d.length - 1; 0 <= g; g--) {
        var h = d[g], k2 = h.instance, l2 = h.currentTarget;
        h = h.listener;
        if (k2 !== f2 && e.isPropagationStopped()) break a;
        nf(e, h, l2);
        f2 = k2;
      }
      else for (g = 0; g < d.length; g++) {
        h = d[g];
        k2 = h.instance;
        l2 = h.currentTarget;
        h = h.listener;
        if (k2 !== f2 && e.isPropagationStopped()) break a;
        nf(e, h, l2);
        f2 = k2;
      }
    }
  }
  if (Qb) throw a = Rb, Qb = false, Rb = null, a;
}
function D(a, b) {
  var c = b[of];
  void 0 === c && (c = b[of] = /* @__PURE__ */ new Set());
  var d = a + "__bubble";
  c.has(d) || (pf(b, a, 2, false), c.add(d));
}
function qf(a, b, c) {
  var d = 0;
  b && (d |= 4);
  pf(c, a, d, b);
}
var rf = "_reactListening" + Math.random().toString(36).slice(2);
function sf(a) {
  if (!a[rf]) {
    a[rf] = true;
    da.forEach(function(b2) {
      "selectionchange" !== b2 && (mf.has(b2) || qf(b2, false, a), qf(b2, true, a));
    });
    var b = 9 === a.nodeType ? a : a.ownerDocument;
    null === b || b[rf] || (b[rf] = true, qf("selectionchange", false, b));
  }
}
function pf(a, b, c, d) {
  switch (jd(b)) {
    case 1:
      var e = ed;
      break;
    case 4:
      e = gd;
      break;
    default:
      e = fd;
  }
  c = e.bind(null, b, c, a);
  e = void 0;
  !Lb || "touchstart" !== b && "touchmove" !== b && "wheel" !== b || (e = true);
  d ? void 0 !== e ? a.addEventListener(b, c, { capture: true, passive: e }) : a.addEventListener(b, c, true) : void 0 !== e ? a.addEventListener(b, c, { passive: e }) : a.addEventListener(b, c, false);
}
function hd(a, b, c, d, e) {
  var f2 = d;
  if (0 === (b & 1) && 0 === (b & 2) && null !== d) a: for (; ; ) {
    if (null === d) return;
    var g = d.tag;
    if (3 === g || 4 === g) {
      var h = d.stateNode.containerInfo;
      if (h === e || 8 === h.nodeType && h.parentNode === e) break;
      if (4 === g) for (g = d.return; null !== g; ) {
        var k2 = g.tag;
        if (3 === k2 || 4 === k2) {
          if (k2 = g.stateNode.containerInfo, k2 === e || 8 === k2.nodeType && k2.parentNode === e) return;
        }
        g = g.return;
      }
      for (; null !== h; ) {
        g = Wc(h);
        if (null === g) return;
        k2 = g.tag;
        if (5 === k2 || 6 === k2) {
          d = f2 = g;
          continue a;
        }
        h = h.parentNode;
      }
    }
    d = d.return;
  }
  Jb(function() {
    var d2 = f2, e2 = xb(c), g2 = [];
    a: {
      var h2 = df.get(a);
      if (void 0 !== h2) {
        var k3 = td, n2 = a;
        switch (a) {
          case "keypress":
            if (0 === od(c)) break a;
          case "keydown":
          case "keyup":
            k3 = Rd;
            break;
          case "focusin":
            n2 = "focus";
            k3 = Fd;
            break;
          case "focusout":
            n2 = "blur";
            k3 = Fd;
            break;
          case "beforeblur":
          case "afterblur":
            k3 = Fd;
            break;
          case "click":
            if (2 === c.button) break a;
          case "auxclick":
          case "dblclick":
          case "mousedown":
          case "mousemove":
          case "mouseup":
          case "mouseout":
          case "mouseover":
          case "contextmenu":
            k3 = Bd;
            break;
          case "drag":
          case "dragend":
          case "dragenter":
          case "dragexit":
          case "dragleave":
          case "dragover":
          case "dragstart":
          case "drop":
            k3 = Dd;
            break;
          case "touchcancel":
          case "touchend":
          case "touchmove":
          case "touchstart":
            k3 = Vd;
            break;
          case $e:
          case af:
          case bf:
            k3 = Hd;
            break;
          case cf:
            k3 = Xd;
            break;
          case "scroll":
            k3 = vd;
            break;
          case "wheel":
            k3 = Zd;
            break;
          case "copy":
          case "cut":
          case "paste":
            k3 = Jd;
            break;
          case "gotpointercapture":
          case "lostpointercapture":
          case "pointercancel":
          case "pointerdown":
          case "pointermove":
          case "pointerout":
          case "pointerover":
          case "pointerup":
            k3 = Td;
        }
        var t2 = 0 !== (b & 4), J2 = !t2 && "scroll" === a, x2 = t2 ? null !== h2 ? h2 + "Capture" : null : h2;
        t2 = [];
        for (var w2 = d2, u2; null !== w2; ) {
          u2 = w2;
          var F2 = u2.stateNode;
          5 === u2.tag && null !== F2 && (u2 = F2, null !== x2 && (F2 = Kb(w2, x2), null != F2 && t2.push(tf(w2, F2, u2))));
          if (J2) break;
          w2 = w2.return;
        }
        0 < t2.length && (h2 = new k3(h2, n2, null, c, e2), g2.push({ event: h2, listeners: t2 }));
      }
    }
    if (0 === (b & 7)) {
      a: {
        h2 = "mouseover" === a || "pointerover" === a;
        k3 = "mouseout" === a || "pointerout" === a;
        if (h2 && c !== wb && (n2 = c.relatedTarget || c.fromElement) && (Wc(n2) || n2[uf])) break a;
        if (k3 || h2) {
          h2 = e2.window === e2 ? e2 : (h2 = e2.ownerDocument) ? h2.defaultView || h2.parentWindow : window;
          if (k3) {
            if (n2 = c.relatedTarget || c.toElement, k3 = d2, n2 = n2 ? Wc(n2) : null, null !== n2 && (J2 = Vb(n2), n2 !== J2 || 5 !== n2.tag && 6 !== n2.tag)) n2 = null;
          } else k3 = null, n2 = d2;
          if (k3 !== n2) {
            t2 = Bd;
            F2 = "onMouseLeave";
            x2 = "onMouseEnter";
            w2 = "mouse";
            if ("pointerout" === a || "pointerover" === a) t2 = Td, F2 = "onPointerLeave", x2 = "onPointerEnter", w2 = "pointer";
            J2 = null == k3 ? h2 : ue(k3);
            u2 = null == n2 ? h2 : ue(n2);
            h2 = new t2(F2, w2 + "leave", k3, c, e2);
            h2.target = J2;
            h2.relatedTarget = u2;
            F2 = null;
            Wc(e2) === d2 && (t2 = new t2(x2, w2 + "enter", n2, c, e2), t2.target = u2, t2.relatedTarget = J2, F2 = t2);
            J2 = F2;
            if (k3 && n2) b: {
              t2 = k3;
              x2 = n2;
              w2 = 0;
              for (u2 = t2; u2; u2 = vf(u2)) w2++;
              u2 = 0;
              for (F2 = x2; F2; F2 = vf(F2)) u2++;
              for (; 0 < w2 - u2; ) t2 = vf(t2), w2--;
              for (; 0 < u2 - w2; ) x2 = vf(x2), u2--;
              for (; w2--; ) {
                if (t2 === x2 || null !== x2 && t2 === x2.alternate) break b;
                t2 = vf(t2);
                x2 = vf(x2);
              }
              t2 = null;
            }
            else t2 = null;
            null !== k3 && wf(g2, h2, k3, t2, false);
            null !== n2 && null !== J2 && wf(g2, J2, n2, t2, true);
          }
        }
      }
      a: {
        h2 = d2 ? ue(d2) : window;
        k3 = h2.nodeName && h2.nodeName.toLowerCase();
        if ("select" === k3 || "input" === k3 && "file" === h2.type) var na = ve;
        else if (me(h2)) if (we) na = Fe;
        else {
          na = De;
          var xa = Ce;
        }
        else (k3 = h2.nodeName) && "input" === k3.toLowerCase() && ("checkbox" === h2.type || "radio" === h2.type) && (na = Ee);
        if (na && (na = na(a, d2))) {
          ne(g2, na, c, e2);
          break a;
        }
        xa && xa(a, h2, d2);
        "focusout" === a && (xa = h2._wrapperState) && xa.controlled && "number" === h2.type && cb(h2, "number", h2.value);
      }
      xa = d2 ? ue(d2) : window;
      switch (a) {
        case "focusin":
          if (me(xa) || "true" === xa.contentEditable) Qe = xa, Re = d2, Se = null;
          break;
        case "focusout":
          Se = Re = Qe = null;
          break;
        case "mousedown":
          Te = true;
          break;
        case "contextmenu":
        case "mouseup":
        case "dragend":
          Te = false;
          Ue(g2, c, e2);
          break;
        case "selectionchange":
          if (Pe) break;
        case "keydown":
        case "keyup":
          Ue(g2, c, e2);
      }
      var $a;
      if (ae) b: {
        switch (a) {
          case "compositionstart":
            var ba = "onCompositionStart";
            break b;
          case "compositionend":
            ba = "onCompositionEnd";
            break b;
          case "compositionupdate":
            ba = "onCompositionUpdate";
            break b;
        }
        ba = void 0;
      }
      else ie ? ge(a, c) && (ba = "onCompositionEnd") : "keydown" === a && 229 === c.keyCode && (ba = "onCompositionStart");
      ba && (de && "ko" !== c.locale && (ie || "onCompositionStart" !== ba ? "onCompositionEnd" === ba && ie && ($a = nd()) : (kd = e2, ld = "value" in kd ? kd.value : kd.textContent, ie = true)), xa = oe(d2, ba), 0 < xa.length && (ba = new Ld(ba, a, null, c, e2), g2.push({ event: ba, listeners: xa }), $a ? ba.data = $a : ($a = he(c), null !== $a && (ba.data = $a))));
      if ($a = ce ? je(a, c) : ke(a, c)) d2 = oe(d2, "onBeforeInput"), 0 < d2.length && (e2 = new Ld("onBeforeInput", "beforeinput", null, c, e2), g2.push({ event: e2, listeners: d2 }), e2.data = $a);
    }
    se(g2, b);
  });
}
function tf(a, b, c) {
  return { instance: a, listener: b, currentTarget: c };
}
function oe(a, b) {
  for (var c = b + "Capture", d = []; null !== a; ) {
    var e = a, f2 = e.stateNode;
    5 === e.tag && null !== f2 && (e = f2, f2 = Kb(a, c), null != f2 && d.unshift(tf(a, f2, e)), f2 = Kb(a, b), null != f2 && d.push(tf(a, f2, e)));
    a = a.return;
  }
  return d;
}
function vf(a) {
  if (null === a) return null;
  do
    a = a.return;
  while (a && 5 !== a.tag);
  return a ? a : null;
}
function wf(a, b, c, d, e) {
  for (var f2 = b._reactName, g = []; null !== c && c !== d; ) {
    var h = c, k2 = h.alternate, l2 = h.stateNode;
    if (null !== k2 && k2 === d) break;
    5 === h.tag && null !== l2 && (h = l2, e ? (k2 = Kb(c, f2), null != k2 && g.unshift(tf(c, k2, h))) : e || (k2 = Kb(c, f2), null != k2 && g.push(tf(c, k2, h))));
    c = c.return;
  }
  0 !== g.length && a.push({ event: b, listeners: g });
}
var xf = /\r\n?/g, yf = /\u0000|\uFFFD/g;
function zf(a) {
  return ("string" === typeof a ? a : "" + a).replace(xf, "\n").replace(yf, "");
}
function Af(a, b, c) {
  b = zf(b);
  if (zf(a) !== b && c) throw Error(p(425));
}
function Bf() {
}
var Cf = null, Df = null;
function Ef(a, b) {
  return "textarea" === a || "noscript" === a || "string" === typeof b.children || "number" === typeof b.children || "object" === typeof b.dangerouslySetInnerHTML && null !== b.dangerouslySetInnerHTML && null != b.dangerouslySetInnerHTML.__html;
}
var Ff = "function" === typeof setTimeout ? setTimeout : void 0, Gf = "function" === typeof clearTimeout ? clearTimeout : void 0, Hf = "function" === typeof Promise ? Promise : void 0, Jf = "function" === typeof queueMicrotask ? queueMicrotask : "undefined" !== typeof Hf ? function(a) {
  return Hf.resolve(null).then(a).catch(If);
} : Ff;
function If(a) {
  setTimeout(function() {
    throw a;
  });
}
function Kf(a, b) {
  var c = b, d = 0;
  do {
    var e = c.nextSibling;
    a.removeChild(c);
    if (e && 8 === e.nodeType) if (c = e.data, "/$" === c) {
      if (0 === d) {
        a.removeChild(e);
        bd(b);
        return;
      }
      d--;
    } else "$" !== c && "$?" !== c && "$!" !== c || d++;
    c = e;
  } while (c);
  bd(b);
}
function Lf(a) {
  for (; null != a; a = a.nextSibling) {
    var b = a.nodeType;
    if (1 === b || 3 === b) break;
    if (8 === b) {
      b = a.data;
      if ("$" === b || "$!" === b || "$?" === b) break;
      if ("/$" === b) return null;
    }
  }
  return a;
}
function Mf(a) {
  a = a.previousSibling;
  for (var b = 0; a; ) {
    if (8 === a.nodeType) {
      var c = a.data;
      if ("$" === c || "$!" === c || "$?" === c) {
        if (0 === b) return a;
        b--;
      } else "/$" === c && b++;
    }
    a = a.previousSibling;
  }
  return null;
}
var Nf = Math.random().toString(36).slice(2), Of = "__reactFiber$" + Nf, Pf = "__reactProps$" + Nf, uf = "__reactContainer$" + Nf, of = "__reactEvents$" + Nf, Qf = "__reactListeners$" + Nf, Rf = "__reactHandles$" + Nf;
function Wc(a) {
  var b = a[Of];
  if (b) return b;
  for (var c = a.parentNode; c; ) {
    if (b = c[uf] || c[Of]) {
      c = b.alternate;
      if (null !== b.child || null !== c && null !== c.child) for (a = Mf(a); null !== a; ) {
        if (c = a[Of]) return c;
        a = Mf(a);
      }
      return b;
    }
    a = c;
    c = a.parentNode;
  }
  return null;
}
function Cb(a) {
  a = a[Of] || a[uf];
  return !a || 5 !== a.tag && 6 !== a.tag && 13 !== a.tag && 3 !== a.tag ? null : a;
}
function ue(a) {
  if (5 === a.tag || 6 === a.tag) return a.stateNode;
  throw Error(p(33));
}
function Db(a) {
  return a[Pf] || null;
}
var Sf = [], Tf = -1;
function Uf(a) {
  return { current: a };
}
function E(a) {
  0 > Tf || (a.current = Sf[Tf], Sf[Tf] = null, Tf--);
}
function G(a, b) {
  Tf++;
  Sf[Tf] = a.current;
  a.current = b;
}
var Vf = {}, H = Uf(Vf), Wf = Uf(false), Xf = Vf;
function Yf(a, b) {
  var c = a.type.contextTypes;
  if (!c) return Vf;
  var d = a.stateNode;
  if (d && d.__reactInternalMemoizedUnmaskedChildContext === b) return d.__reactInternalMemoizedMaskedChildContext;
  var e = {}, f2;
  for (f2 in c) e[f2] = b[f2];
  d && (a = a.stateNode, a.__reactInternalMemoizedUnmaskedChildContext = b, a.__reactInternalMemoizedMaskedChildContext = e);
  return e;
}
function Zf(a) {
  a = a.childContextTypes;
  return null !== a && void 0 !== a;
}
function $f() {
  E(Wf);
  E(H);
}
function ag(a, b, c) {
  if (H.current !== Vf) throw Error(p(168));
  G(H, b);
  G(Wf, c);
}
function bg(a, b, c) {
  var d = a.stateNode;
  b = b.childContextTypes;
  if ("function" !== typeof d.getChildContext) return c;
  d = d.getChildContext();
  for (var e in d) if (!(e in b)) throw Error(p(108, Ra(a) || "Unknown", e));
  return A({}, c, d);
}
function cg(a) {
  a = (a = a.stateNode) && a.__reactInternalMemoizedMergedChildContext || Vf;
  Xf = H.current;
  G(H, a);
  G(Wf, Wf.current);
  return true;
}
function dg(a, b, c) {
  var d = a.stateNode;
  if (!d) throw Error(p(169));
  c ? (a = bg(a, b, Xf), d.__reactInternalMemoizedMergedChildContext = a, E(Wf), E(H), G(H, a)) : E(Wf);
  G(Wf, c);
}
var eg = null, fg = false, gg = false;
function hg(a) {
  null === eg ? eg = [a] : eg.push(a);
}
function ig(a) {
  fg = true;
  hg(a);
}
function jg() {
  if (!gg && null !== eg) {
    gg = true;
    var a = 0, b = C;
    try {
      var c = eg;
      for (C = 1; a < c.length; a++) {
        var d = c[a];
        do
          d = d(true);
        while (null !== d);
      }
      eg = null;
      fg = false;
    } catch (e) {
      throw null !== eg && (eg = eg.slice(a + 1)), ac(fc, jg), e;
    } finally {
      C = b, gg = false;
    }
  }
  return null;
}
var kg = [], lg = 0, mg = null, ng = 0, og = [], pg = 0, qg = null, rg = 1, sg = "";
function tg(a, b) {
  kg[lg++] = ng;
  kg[lg++] = mg;
  mg = a;
  ng = b;
}
function ug(a, b, c) {
  og[pg++] = rg;
  og[pg++] = sg;
  og[pg++] = qg;
  qg = a;
  var d = rg;
  a = sg;
  var e = 32 - oc(d) - 1;
  d &= ~(1 << e);
  c += 1;
  var f2 = 32 - oc(b) + e;
  if (30 < f2) {
    var g = e - e % 5;
    f2 = (d & (1 << g) - 1).toString(32);
    d >>= g;
    e -= g;
    rg = 1 << 32 - oc(b) + e | c << e | d;
    sg = f2 + a;
  } else rg = 1 << f2 | c << e | d, sg = a;
}
function vg(a) {
  null !== a.return && (tg(a, 1), ug(a, 1, 0));
}
function wg(a) {
  for (; a === mg; ) mg = kg[--lg], kg[lg] = null, ng = kg[--lg], kg[lg] = null;
  for (; a === qg; ) qg = og[--pg], og[pg] = null, sg = og[--pg], og[pg] = null, rg = og[--pg], og[pg] = null;
}
var xg = null, yg = null, I = false, zg = null;
function Ag(a, b) {
  var c = Bg(5, null, null, 0);
  c.elementType = "DELETED";
  c.stateNode = b;
  c.return = a;
  b = a.deletions;
  null === b ? (a.deletions = [c], a.flags |= 16) : b.push(c);
}
function Cg(a, b) {
  switch (a.tag) {
    case 5:
      var c = a.type;
      b = 1 !== b.nodeType || c.toLowerCase() !== b.nodeName.toLowerCase() ? null : b;
      return null !== b ? (a.stateNode = b, xg = a, yg = Lf(b.firstChild), true) : false;
    case 6:
      return b = "" === a.pendingProps || 3 !== b.nodeType ? null : b, null !== b ? (a.stateNode = b, xg = a, yg = null, true) : false;
    case 13:
      return b = 8 !== b.nodeType ? null : b, null !== b ? (c = null !== qg ? { id: rg, overflow: sg } : null, a.memoizedState = { dehydrated: b, treeContext: c, retryLane: 1073741824 }, c = Bg(18, null, null, 0), c.stateNode = b, c.return = a, a.child = c, xg = a, yg = null, true) : false;
    default:
      return false;
  }
}
function Dg(a) {
  return 0 !== (a.mode & 1) && 0 === (a.flags & 128);
}
function Eg(a) {
  if (I) {
    var b = yg;
    if (b) {
      var c = b;
      if (!Cg(a, b)) {
        if (Dg(a)) throw Error(p(418));
        b = Lf(c.nextSibling);
        var d = xg;
        b && Cg(a, b) ? Ag(d, c) : (a.flags = a.flags & -4097 | 2, I = false, xg = a);
      }
    } else {
      if (Dg(a)) throw Error(p(418));
      a.flags = a.flags & -4097 | 2;
      I = false;
      xg = a;
    }
  }
}
function Fg(a) {
  for (a = a.return; null !== a && 5 !== a.tag && 3 !== a.tag && 13 !== a.tag; ) a = a.return;
  xg = a;
}
function Gg(a) {
  if (a !== xg) return false;
  if (!I) return Fg(a), I = true, false;
  var b;
  (b = 3 !== a.tag) && !(b = 5 !== a.tag) && (b = a.type, b = "head" !== b && "body" !== b && !Ef(a.type, a.memoizedProps));
  if (b && (b = yg)) {
    if (Dg(a)) throw Hg(), Error(p(418));
    for (; b; ) Ag(a, b), b = Lf(b.nextSibling);
  }
  Fg(a);
  if (13 === a.tag) {
    a = a.memoizedState;
    a = null !== a ? a.dehydrated : null;
    if (!a) throw Error(p(317));
    a: {
      a = a.nextSibling;
      for (b = 0; a; ) {
        if (8 === a.nodeType) {
          var c = a.data;
          if ("/$" === c) {
            if (0 === b) {
              yg = Lf(a.nextSibling);
              break a;
            }
            b--;
          } else "$" !== c && "$!" !== c && "$?" !== c || b++;
        }
        a = a.nextSibling;
      }
      yg = null;
    }
  } else yg = xg ? Lf(a.stateNode.nextSibling) : null;
  return true;
}
function Hg() {
  for (var a = yg; a; ) a = Lf(a.nextSibling);
}
function Ig() {
  yg = xg = null;
  I = false;
}
function Jg(a) {
  null === zg ? zg = [a] : zg.push(a);
}
var Kg = ua.ReactCurrentBatchConfig;
function Lg(a, b, c) {
  a = c.ref;
  if (null !== a && "function" !== typeof a && "object" !== typeof a) {
    if (c._owner) {
      c = c._owner;
      if (c) {
        if (1 !== c.tag) throw Error(p(309));
        var d = c.stateNode;
      }
      if (!d) throw Error(p(147, a));
      var e = d, f2 = "" + a;
      if (null !== b && null !== b.ref && "function" === typeof b.ref && b.ref._stringRef === f2) return b.ref;
      b = function(a2) {
        var b2 = e.refs;
        null === a2 ? delete b2[f2] : b2[f2] = a2;
      };
      b._stringRef = f2;
      return b;
    }
    if ("string" !== typeof a) throw Error(p(284));
    if (!c._owner) throw Error(p(290, a));
  }
  return a;
}
function Mg(a, b) {
  a = Object.prototype.toString.call(b);
  throw Error(p(31, "[object Object]" === a ? "object with keys {" + Object.keys(b).join(", ") + "}" : a));
}
function Ng(a) {
  var b = a._init;
  return b(a._payload);
}
function Og(a) {
  function b(b2, c2) {
    if (a) {
      var d2 = b2.deletions;
      null === d2 ? (b2.deletions = [c2], b2.flags |= 16) : d2.push(c2);
    }
  }
  function c(c2, d2) {
    if (!a) return null;
    for (; null !== d2; ) b(c2, d2), d2 = d2.sibling;
    return null;
  }
  function d(a2, b2) {
    for (a2 = /* @__PURE__ */ new Map(); null !== b2; ) null !== b2.key ? a2.set(b2.key, b2) : a2.set(b2.index, b2), b2 = b2.sibling;
    return a2;
  }
  function e(a2, b2) {
    a2 = Pg(a2, b2);
    a2.index = 0;
    a2.sibling = null;
    return a2;
  }
  function f2(b2, c2, d2) {
    b2.index = d2;
    if (!a) return b2.flags |= 1048576, c2;
    d2 = b2.alternate;
    if (null !== d2) return d2 = d2.index, d2 < c2 ? (b2.flags |= 2, c2) : d2;
    b2.flags |= 2;
    return c2;
  }
  function g(b2) {
    a && null === b2.alternate && (b2.flags |= 2);
    return b2;
  }
  function h(a2, b2, c2, d2) {
    if (null === b2 || 6 !== b2.tag) return b2 = Qg(c2, a2.mode, d2), b2.return = a2, b2;
    b2 = e(b2, c2);
    b2.return = a2;
    return b2;
  }
  function k2(a2, b2, c2, d2) {
    var f3 = c2.type;
    if (f3 === ya) return m2(a2, b2, c2.props.children, d2, c2.key);
    if (null !== b2 && (b2.elementType === f3 || "object" === typeof f3 && null !== f3 && f3.$$typeof === Ha && Ng(f3) === b2.type)) return d2 = e(b2, c2.props), d2.ref = Lg(a2, b2, c2), d2.return = a2, d2;
    d2 = Rg(c2.type, c2.key, c2.props, null, a2.mode, d2);
    d2.ref = Lg(a2, b2, c2);
    d2.return = a2;
    return d2;
  }
  function l2(a2, b2, c2, d2) {
    if (null === b2 || 4 !== b2.tag || b2.stateNode.containerInfo !== c2.containerInfo || b2.stateNode.implementation !== c2.implementation) return b2 = Sg(c2, a2.mode, d2), b2.return = a2, b2;
    b2 = e(b2, c2.children || []);
    b2.return = a2;
    return b2;
  }
  function m2(a2, b2, c2, d2, f3) {
    if (null === b2 || 7 !== b2.tag) return b2 = Tg(c2, a2.mode, d2, f3), b2.return = a2, b2;
    b2 = e(b2, c2);
    b2.return = a2;
    return b2;
  }
  function q2(a2, b2, c2) {
    if ("string" === typeof b2 && "" !== b2 || "number" === typeof b2) return b2 = Qg("" + b2, a2.mode, c2), b2.return = a2, b2;
    if ("object" === typeof b2 && null !== b2) {
      switch (b2.$$typeof) {
        case va:
          return c2 = Rg(b2.type, b2.key, b2.props, null, a2.mode, c2), c2.ref = Lg(a2, null, b2), c2.return = a2, c2;
        case wa:
          return b2 = Sg(b2, a2.mode, c2), b2.return = a2, b2;
        case Ha:
          var d2 = b2._init;
          return q2(a2, d2(b2._payload), c2);
      }
      if (eb(b2) || Ka(b2)) return b2 = Tg(b2, a2.mode, c2, null), b2.return = a2, b2;
      Mg(a2, b2);
    }
    return null;
  }
  function r2(a2, b2, c2, d2) {
    var e2 = null !== b2 ? b2.key : null;
    if ("string" === typeof c2 && "" !== c2 || "number" === typeof c2) return null !== e2 ? null : h(a2, b2, "" + c2, d2);
    if ("object" === typeof c2 && null !== c2) {
      switch (c2.$$typeof) {
        case va:
          return c2.key === e2 ? k2(a2, b2, c2, d2) : null;
        case wa:
          return c2.key === e2 ? l2(a2, b2, c2, d2) : null;
        case Ha:
          return e2 = c2._init, r2(
            a2,
            b2,
            e2(c2._payload),
            d2
          );
      }
      if (eb(c2) || Ka(c2)) return null !== e2 ? null : m2(a2, b2, c2, d2, null);
      Mg(a2, c2);
    }
    return null;
  }
  function y2(a2, b2, c2, d2, e2) {
    if ("string" === typeof d2 && "" !== d2 || "number" === typeof d2) return a2 = a2.get(c2) || null, h(b2, a2, "" + d2, e2);
    if ("object" === typeof d2 && null !== d2) {
      switch (d2.$$typeof) {
        case va:
          return a2 = a2.get(null === d2.key ? c2 : d2.key) || null, k2(b2, a2, d2, e2);
        case wa:
          return a2 = a2.get(null === d2.key ? c2 : d2.key) || null, l2(b2, a2, d2, e2);
        case Ha:
          var f3 = d2._init;
          return y2(a2, b2, c2, f3(d2._payload), e2);
      }
      if (eb(d2) || Ka(d2)) return a2 = a2.get(c2) || null, m2(b2, a2, d2, e2, null);
      Mg(b2, d2);
    }
    return null;
  }
  function n2(e2, g2, h2, k3) {
    for (var l3 = null, m3 = null, u2 = g2, w2 = g2 = 0, x2 = null; null !== u2 && w2 < h2.length; w2++) {
      u2.index > w2 ? (x2 = u2, u2 = null) : x2 = u2.sibling;
      var n3 = r2(e2, u2, h2[w2], k3);
      if (null === n3) {
        null === u2 && (u2 = x2);
        break;
      }
      a && u2 && null === n3.alternate && b(e2, u2);
      g2 = f2(n3, g2, w2);
      null === m3 ? l3 = n3 : m3.sibling = n3;
      m3 = n3;
      u2 = x2;
    }
    if (w2 === h2.length) return c(e2, u2), I && tg(e2, w2), l3;
    if (null === u2) {
      for (; w2 < h2.length; w2++) u2 = q2(e2, h2[w2], k3), null !== u2 && (g2 = f2(u2, g2, w2), null === m3 ? l3 = u2 : m3.sibling = u2, m3 = u2);
      I && tg(e2, w2);
      return l3;
    }
    for (u2 = d(e2, u2); w2 < h2.length; w2++) x2 = y2(u2, e2, w2, h2[w2], k3), null !== x2 && (a && null !== x2.alternate && u2.delete(null === x2.key ? w2 : x2.key), g2 = f2(x2, g2, w2), null === m3 ? l3 = x2 : m3.sibling = x2, m3 = x2);
    a && u2.forEach(function(a2) {
      return b(e2, a2);
    });
    I && tg(e2, w2);
    return l3;
  }
  function t2(e2, g2, h2, k3) {
    var l3 = Ka(h2);
    if ("function" !== typeof l3) throw Error(p(150));
    h2 = l3.call(h2);
    if (null == h2) throw Error(p(151));
    for (var u2 = l3 = null, m3 = g2, w2 = g2 = 0, x2 = null, n3 = h2.next(); null !== m3 && !n3.done; w2++, n3 = h2.next()) {
      m3.index > w2 ? (x2 = m3, m3 = null) : x2 = m3.sibling;
      var t3 = r2(e2, m3, n3.value, k3);
      if (null === t3) {
        null === m3 && (m3 = x2);
        break;
      }
      a && m3 && null === t3.alternate && b(e2, m3);
      g2 = f2(t3, g2, w2);
      null === u2 ? l3 = t3 : u2.sibling = t3;
      u2 = t3;
      m3 = x2;
    }
    if (n3.done) return c(
      e2,
      m3
    ), I && tg(e2, w2), l3;
    if (null === m3) {
      for (; !n3.done; w2++, n3 = h2.next()) n3 = q2(e2, n3.value, k3), null !== n3 && (g2 = f2(n3, g2, w2), null === u2 ? l3 = n3 : u2.sibling = n3, u2 = n3);
      I && tg(e2, w2);
      return l3;
    }
    for (m3 = d(e2, m3); !n3.done; w2++, n3 = h2.next()) n3 = y2(m3, e2, w2, n3.value, k3), null !== n3 && (a && null !== n3.alternate && m3.delete(null === n3.key ? w2 : n3.key), g2 = f2(n3, g2, w2), null === u2 ? l3 = n3 : u2.sibling = n3, u2 = n3);
    a && m3.forEach(function(a2) {
      return b(e2, a2);
    });
    I && tg(e2, w2);
    return l3;
  }
  function J2(a2, d2, f3, h2) {
    "object" === typeof f3 && null !== f3 && f3.type === ya && null === f3.key && (f3 = f3.props.children);
    if ("object" === typeof f3 && null !== f3) {
      switch (f3.$$typeof) {
        case va:
          a: {
            for (var k3 = f3.key, l3 = d2; null !== l3; ) {
              if (l3.key === k3) {
                k3 = f3.type;
                if (k3 === ya) {
                  if (7 === l3.tag) {
                    c(a2, l3.sibling);
                    d2 = e(l3, f3.props.children);
                    d2.return = a2;
                    a2 = d2;
                    break a;
                  }
                } else if (l3.elementType === k3 || "object" === typeof k3 && null !== k3 && k3.$$typeof === Ha && Ng(k3) === l3.type) {
                  c(a2, l3.sibling);
                  d2 = e(l3, f3.props);
                  d2.ref = Lg(a2, l3, f3);
                  d2.return = a2;
                  a2 = d2;
                  break a;
                }
                c(a2, l3);
                break;
              } else b(a2, l3);
              l3 = l3.sibling;
            }
            f3.type === ya ? (d2 = Tg(f3.props.children, a2.mode, h2, f3.key), d2.return = a2, a2 = d2) : (h2 = Rg(f3.type, f3.key, f3.props, null, a2.mode, h2), h2.ref = Lg(a2, d2, f3), h2.return = a2, a2 = h2);
          }
          return g(a2);
        case wa:
          a: {
            for (l3 = f3.key; null !== d2; ) {
              if (d2.key === l3) if (4 === d2.tag && d2.stateNode.containerInfo === f3.containerInfo && d2.stateNode.implementation === f3.implementation) {
                c(a2, d2.sibling);
                d2 = e(d2, f3.children || []);
                d2.return = a2;
                a2 = d2;
                break a;
              } else {
                c(a2, d2);
                break;
              }
              else b(a2, d2);
              d2 = d2.sibling;
            }
            d2 = Sg(f3, a2.mode, h2);
            d2.return = a2;
            a2 = d2;
          }
          return g(a2);
        case Ha:
          return l3 = f3._init, J2(a2, d2, l3(f3._payload), h2);
      }
      if (eb(f3)) return n2(a2, d2, f3, h2);
      if (Ka(f3)) return t2(a2, d2, f3, h2);
      Mg(a2, f3);
    }
    return "string" === typeof f3 && "" !== f3 || "number" === typeof f3 ? (f3 = "" + f3, null !== d2 && 6 === d2.tag ? (c(a2, d2.sibling), d2 = e(d2, f3), d2.return = a2, a2 = d2) : (c(a2, d2), d2 = Qg(f3, a2.mode, h2), d2.return = a2, a2 = d2), g(a2)) : c(a2, d2);
  }
  return J2;
}
var Ug = Og(true), Vg = Og(false), Wg = Uf(null), Xg = null, Yg = null, Zg = null;
function $g() {
  Zg = Yg = Xg = null;
}
function ah(a) {
  var b = Wg.current;
  E(Wg);
  a._currentValue = b;
}
function bh(a, b, c) {
  for (; null !== a; ) {
    var d = a.alternate;
    (a.childLanes & b) !== b ? (a.childLanes |= b, null !== d && (d.childLanes |= b)) : null !== d && (d.childLanes & b) !== b && (d.childLanes |= b);
    if (a === c) break;
    a = a.return;
  }
}
function ch(a, b) {
  Xg = a;
  Zg = Yg = null;
  a = a.dependencies;
  null !== a && null !== a.firstContext && (0 !== (a.lanes & b) && (dh = true), a.firstContext = null);
}
function eh(a) {
  var b = a._currentValue;
  if (Zg !== a) if (a = { context: a, memoizedValue: b, next: null }, null === Yg) {
    if (null === Xg) throw Error(p(308));
    Yg = a;
    Xg.dependencies = { lanes: 0, firstContext: a };
  } else Yg = Yg.next = a;
  return b;
}
var fh = null;
function gh(a) {
  null === fh ? fh = [a] : fh.push(a);
}
function hh(a, b, c, d) {
  var e = b.interleaved;
  null === e ? (c.next = c, gh(b)) : (c.next = e.next, e.next = c);
  b.interleaved = c;
  return ih(a, d);
}
function ih(a, b) {
  a.lanes |= b;
  var c = a.alternate;
  null !== c && (c.lanes |= b);
  c = a;
  for (a = a.return; null !== a; ) a.childLanes |= b, c = a.alternate, null !== c && (c.childLanes |= b), c = a, a = a.return;
  return 3 === c.tag ? c.stateNode : null;
}
var jh = false;
function kh(a) {
  a.updateQueue = { baseState: a.memoizedState, firstBaseUpdate: null, lastBaseUpdate: null, shared: { pending: null, interleaved: null, lanes: 0 }, effects: null };
}
function lh(a, b) {
  a = a.updateQueue;
  b.updateQueue === a && (b.updateQueue = { baseState: a.baseState, firstBaseUpdate: a.firstBaseUpdate, lastBaseUpdate: a.lastBaseUpdate, shared: a.shared, effects: a.effects });
}
function mh(a, b) {
  return { eventTime: a, lane: b, tag: 0, payload: null, callback: null, next: null };
}
function nh(a, b, c) {
  var d = a.updateQueue;
  if (null === d) return null;
  d = d.shared;
  if (0 !== (K & 2)) {
    var e = d.pending;
    null === e ? b.next = b : (b.next = e.next, e.next = b);
    d.pending = b;
    return ih(a, c);
  }
  e = d.interleaved;
  null === e ? (b.next = b, gh(d)) : (b.next = e.next, e.next = b);
  d.interleaved = b;
  return ih(a, c);
}
function oh(a, b, c) {
  b = b.updateQueue;
  if (null !== b && (b = b.shared, 0 !== (c & 4194240))) {
    var d = b.lanes;
    d &= a.pendingLanes;
    c |= d;
    b.lanes = c;
    Cc(a, c);
  }
}
function ph(a, b) {
  var c = a.updateQueue, d = a.alternate;
  if (null !== d && (d = d.updateQueue, c === d)) {
    var e = null, f2 = null;
    c = c.firstBaseUpdate;
    if (null !== c) {
      do {
        var g = { eventTime: c.eventTime, lane: c.lane, tag: c.tag, payload: c.payload, callback: c.callback, next: null };
        null === f2 ? e = f2 = g : f2 = f2.next = g;
        c = c.next;
      } while (null !== c);
      null === f2 ? e = f2 = b : f2 = f2.next = b;
    } else e = f2 = b;
    c = { baseState: d.baseState, firstBaseUpdate: e, lastBaseUpdate: f2, shared: d.shared, effects: d.effects };
    a.updateQueue = c;
    return;
  }
  a = c.lastBaseUpdate;
  null === a ? c.firstBaseUpdate = b : a.next = b;
  c.lastBaseUpdate = b;
}
function qh(a, b, c, d) {
  var e = a.updateQueue;
  jh = false;
  var f2 = e.firstBaseUpdate, g = e.lastBaseUpdate, h = e.shared.pending;
  if (null !== h) {
    e.shared.pending = null;
    var k2 = h, l2 = k2.next;
    k2.next = null;
    null === g ? f2 = l2 : g.next = l2;
    g = k2;
    var m2 = a.alternate;
    null !== m2 && (m2 = m2.updateQueue, h = m2.lastBaseUpdate, h !== g && (null === h ? m2.firstBaseUpdate = l2 : h.next = l2, m2.lastBaseUpdate = k2));
  }
  if (null !== f2) {
    var q2 = e.baseState;
    g = 0;
    m2 = l2 = k2 = null;
    h = f2;
    do {
      var r2 = h.lane, y2 = h.eventTime;
      if ((d & r2) === r2) {
        null !== m2 && (m2 = m2.next = {
          eventTime: y2,
          lane: 0,
          tag: h.tag,
          payload: h.payload,
          callback: h.callback,
          next: null
        });
        a: {
          var n2 = a, t2 = h;
          r2 = b;
          y2 = c;
          switch (t2.tag) {
            case 1:
              n2 = t2.payload;
              if ("function" === typeof n2) {
                q2 = n2.call(y2, q2, r2);
                break a;
              }
              q2 = n2;
              break a;
            case 3:
              n2.flags = n2.flags & -65537 | 128;
            case 0:
              n2 = t2.payload;
              r2 = "function" === typeof n2 ? n2.call(y2, q2, r2) : n2;
              if (null === r2 || void 0 === r2) break a;
              q2 = A({}, q2, r2);
              break a;
            case 2:
              jh = true;
          }
        }
        null !== h.callback && 0 !== h.lane && (a.flags |= 64, r2 = e.effects, null === r2 ? e.effects = [h] : r2.push(h));
      } else y2 = { eventTime: y2, lane: r2, tag: h.tag, payload: h.payload, callback: h.callback, next: null }, null === m2 ? (l2 = m2 = y2, k2 = q2) : m2 = m2.next = y2, g |= r2;
      h = h.next;
      if (null === h) if (h = e.shared.pending, null === h) break;
      else r2 = h, h = r2.next, r2.next = null, e.lastBaseUpdate = r2, e.shared.pending = null;
    } while (1);
    null === m2 && (k2 = q2);
    e.baseState = k2;
    e.firstBaseUpdate = l2;
    e.lastBaseUpdate = m2;
    b = e.shared.interleaved;
    if (null !== b) {
      e = b;
      do
        g |= e.lane, e = e.next;
      while (e !== b);
    } else null === f2 && (e.shared.lanes = 0);
    rh |= g;
    a.lanes = g;
    a.memoizedState = q2;
  }
}
function sh(a, b, c) {
  a = b.effects;
  b.effects = null;
  if (null !== a) for (b = 0; b < a.length; b++) {
    var d = a[b], e = d.callback;
    if (null !== e) {
      d.callback = null;
      d = c;
      if ("function" !== typeof e) throw Error(p(191, e));
      e.call(d);
    }
  }
}
var th = {}, uh = Uf(th), vh = Uf(th), wh = Uf(th);
function xh(a) {
  if (a === th) throw Error(p(174));
  return a;
}
function yh(a, b) {
  G(wh, b);
  G(vh, a);
  G(uh, th);
  a = b.nodeType;
  switch (a) {
    case 9:
    case 11:
      b = (b = b.documentElement) ? b.namespaceURI : lb(null, "");
      break;
    default:
      a = 8 === a ? b.parentNode : b, b = a.namespaceURI || null, a = a.tagName, b = lb(b, a);
  }
  E(uh);
  G(uh, b);
}
function zh() {
  E(uh);
  E(vh);
  E(wh);
}
function Ah(a) {
  xh(wh.current);
  var b = xh(uh.current);
  var c = lb(b, a.type);
  b !== c && (G(vh, a), G(uh, c));
}
function Bh(a) {
  vh.current === a && (E(uh), E(vh));
}
var L = Uf(0);
function Ch(a) {
  for (var b = a; null !== b; ) {
    if (13 === b.tag) {
      var c = b.memoizedState;
      if (null !== c && (c = c.dehydrated, null === c || "$?" === c.data || "$!" === c.data)) return b;
    } else if (19 === b.tag && void 0 !== b.memoizedProps.revealOrder) {
      if (0 !== (b.flags & 128)) return b;
    } else if (null !== b.child) {
      b.child.return = b;
      b = b.child;
      continue;
    }
    if (b === a) break;
    for (; null === b.sibling; ) {
      if (null === b.return || b.return === a) return null;
      b = b.return;
    }
    b.sibling.return = b.return;
    b = b.sibling;
  }
  return null;
}
var Dh = [];
function Eh() {
  for (var a = 0; a < Dh.length; a++) Dh[a]._workInProgressVersionPrimary = null;
  Dh.length = 0;
}
var Fh = ua.ReactCurrentDispatcher, Gh = ua.ReactCurrentBatchConfig, Hh = 0, M = null, N = null, O = null, Ih = false, Jh = false, Kh = 0, Lh = 0;
function P() {
  throw Error(p(321));
}
function Mh(a, b) {
  if (null === b) return false;
  for (var c = 0; c < b.length && c < a.length; c++) if (!He(a[c], b[c])) return false;
  return true;
}
function Nh(a, b, c, d, e, f2) {
  Hh = f2;
  M = b;
  b.memoizedState = null;
  b.updateQueue = null;
  b.lanes = 0;
  Fh.current = null === a || null === a.memoizedState ? Oh : Ph;
  a = c(d, e);
  if (Jh) {
    f2 = 0;
    do {
      Jh = false;
      Kh = 0;
      if (25 <= f2) throw Error(p(301));
      f2 += 1;
      O = N = null;
      b.updateQueue = null;
      Fh.current = Qh;
      a = c(d, e);
    } while (Jh);
  }
  Fh.current = Rh;
  b = null !== N && null !== N.next;
  Hh = 0;
  O = N = M = null;
  Ih = false;
  if (b) throw Error(p(300));
  return a;
}
function Sh() {
  var a = 0 !== Kh;
  Kh = 0;
  return a;
}
function Th() {
  var a = { memoizedState: null, baseState: null, baseQueue: null, queue: null, next: null };
  null === O ? M.memoizedState = O = a : O = O.next = a;
  return O;
}
function Uh() {
  if (null === N) {
    var a = M.alternate;
    a = null !== a ? a.memoizedState : null;
  } else a = N.next;
  var b = null === O ? M.memoizedState : O.next;
  if (null !== b) O = b, N = a;
  else {
    if (null === a) throw Error(p(310));
    N = a;
    a = { memoizedState: N.memoizedState, baseState: N.baseState, baseQueue: N.baseQueue, queue: N.queue, next: null };
    null === O ? M.memoizedState = O = a : O = O.next = a;
  }
  return O;
}
function Vh(a, b) {
  return "function" === typeof b ? b(a) : b;
}
function Wh(a) {
  var b = Uh(), c = b.queue;
  if (null === c) throw Error(p(311));
  c.lastRenderedReducer = a;
  var d = N, e = d.baseQueue, f2 = c.pending;
  if (null !== f2) {
    if (null !== e) {
      var g = e.next;
      e.next = f2.next;
      f2.next = g;
    }
    d.baseQueue = e = f2;
    c.pending = null;
  }
  if (null !== e) {
    f2 = e.next;
    d = d.baseState;
    var h = g = null, k2 = null, l2 = f2;
    do {
      var m2 = l2.lane;
      if ((Hh & m2) === m2) null !== k2 && (k2 = k2.next = { lane: 0, action: l2.action, hasEagerState: l2.hasEagerState, eagerState: l2.eagerState, next: null }), d = l2.hasEagerState ? l2.eagerState : a(d, l2.action);
      else {
        var q2 = {
          lane: m2,
          action: l2.action,
          hasEagerState: l2.hasEagerState,
          eagerState: l2.eagerState,
          next: null
        };
        null === k2 ? (h = k2 = q2, g = d) : k2 = k2.next = q2;
        M.lanes |= m2;
        rh |= m2;
      }
      l2 = l2.next;
    } while (null !== l2 && l2 !== f2);
    null === k2 ? g = d : k2.next = h;
    He(d, b.memoizedState) || (dh = true);
    b.memoizedState = d;
    b.baseState = g;
    b.baseQueue = k2;
    c.lastRenderedState = d;
  }
  a = c.interleaved;
  if (null !== a) {
    e = a;
    do
      f2 = e.lane, M.lanes |= f2, rh |= f2, e = e.next;
    while (e !== a);
  } else null === e && (c.lanes = 0);
  return [b.memoizedState, c.dispatch];
}
function Xh(a) {
  var b = Uh(), c = b.queue;
  if (null === c) throw Error(p(311));
  c.lastRenderedReducer = a;
  var d = c.dispatch, e = c.pending, f2 = b.memoizedState;
  if (null !== e) {
    c.pending = null;
    var g = e = e.next;
    do
      f2 = a(f2, g.action), g = g.next;
    while (g !== e);
    He(f2, b.memoizedState) || (dh = true);
    b.memoizedState = f2;
    null === b.baseQueue && (b.baseState = f2);
    c.lastRenderedState = f2;
  }
  return [f2, d];
}
function Yh() {
}
function Zh(a, b) {
  var c = M, d = Uh(), e = b(), f2 = !He(d.memoizedState, e);
  f2 && (d.memoizedState = e, dh = true);
  d = d.queue;
  $h(ai.bind(null, c, d, a), [a]);
  if (d.getSnapshot !== b || f2 || null !== O && O.memoizedState.tag & 1) {
    c.flags |= 2048;
    bi(9, ci.bind(null, c, d, e, b), void 0, null);
    if (null === Q) throw Error(p(349));
    0 !== (Hh & 30) || di(c, b, e);
  }
  return e;
}
function di(a, b, c) {
  a.flags |= 16384;
  a = { getSnapshot: b, value: c };
  b = M.updateQueue;
  null === b ? (b = { lastEffect: null, stores: null }, M.updateQueue = b, b.stores = [a]) : (c = b.stores, null === c ? b.stores = [a] : c.push(a));
}
function ci(a, b, c, d) {
  b.value = c;
  b.getSnapshot = d;
  ei(b) && fi(a);
}
function ai(a, b, c) {
  return c(function() {
    ei(b) && fi(a);
  });
}
function ei(a) {
  var b = a.getSnapshot;
  a = a.value;
  try {
    var c = b();
    return !He(a, c);
  } catch (d) {
    return true;
  }
}
function fi(a) {
  var b = ih(a, 1);
  null !== b && gi(b, a, 1, -1);
}
function hi(a) {
  var b = Th();
  "function" === typeof a && (a = a());
  b.memoizedState = b.baseState = a;
  a = { pending: null, interleaved: null, lanes: 0, dispatch: null, lastRenderedReducer: Vh, lastRenderedState: a };
  b.queue = a;
  a = a.dispatch = ii.bind(null, M, a);
  return [b.memoizedState, a];
}
function bi(a, b, c, d) {
  a = { tag: a, create: b, destroy: c, deps: d, next: null };
  b = M.updateQueue;
  null === b ? (b = { lastEffect: null, stores: null }, M.updateQueue = b, b.lastEffect = a.next = a) : (c = b.lastEffect, null === c ? b.lastEffect = a.next = a : (d = c.next, c.next = a, a.next = d, b.lastEffect = a));
  return a;
}
function ji() {
  return Uh().memoizedState;
}
function ki(a, b, c, d) {
  var e = Th();
  M.flags |= a;
  e.memoizedState = bi(1 | b, c, void 0, void 0 === d ? null : d);
}
function li(a, b, c, d) {
  var e = Uh();
  d = void 0 === d ? null : d;
  var f2 = void 0;
  if (null !== N) {
    var g = N.memoizedState;
    f2 = g.destroy;
    if (null !== d && Mh(d, g.deps)) {
      e.memoizedState = bi(b, c, f2, d);
      return;
    }
  }
  M.flags |= a;
  e.memoizedState = bi(1 | b, c, f2, d);
}
function mi(a, b) {
  return ki(8390656, 8, a, b);
}
function $h(a, b) {
  return li(2048, 8, a, b);
}
function ni(a, b) {
  return li(4, 2, a, b);
}
function oi(a, b) {
  return li(4, 4, a, b);
}
function pi(a, b) {
  if ("function" === typeof b) return a = a(), b(a), function() {
    b(null);
  };
  if (null !== b && void 0 !== b) return a = a(), b.current = a, function() {
    b.current = null;
  };
}
function qi(a, b, c) {
  c = null !== c && void 0 !== c ? c.concat([a]) : null;
  return li(4, 4, pi.bind(null, b, a), c);
}
function ri() {
}
function si(a, b) {
  var c = Uh();
  b = void 0 === b ? null : b;
  var d = c.memoizedState;
  if (null !== d && null !== b && Mh(b, d[1])) return d[0];
  c.memoizedState = [a, b];
  return a;
}
function ti(a, b) {
  var c = Uh();
  b = void 0 === b ? null : b;
  var d = c.memoizedState;
  if (null !== d && null !== b && Mh(b, d[1])) return d[0];
  a = a();
  c.memoizedState = [a, b];
  return a;
}
function ui(a, b, c) {
  if (0 === (Hh & 21)) return a.baseState && (a.baseState = false, dh = true), a.memoizedState = c;
  He(c, b) || (c = yc(), M.lanes |= c, rh |= c, a.baseState = true);
  return b;
}
function vi(a, b) {
  var c = C;
  C = 0 !== c && 4 > c ? c : 4;
  a(true);
  var d = Gh.transition;
  Gh.transition = {};
  try {
    a(false), b();
  } finally {
    C = c, Gh.transition = d;
  }
}
function wi() {
  return Uh().memoizedState;
}
function xi(a, b, c) {
  var d = yi(a);
  c = { lane: d, action: c, hasEagerState: false, eagerState: null, next: null };
  if (zi(a)) Ai(b, c);
  else if (c = hh(a, b, c, d), null !== c) {
    var e = R();
    gi(c, a, d, e);
    Bi(c, b, d);
  }
}
function ii(a, b, c) {
  var d = yi(a), e = { lane: d, action: c, hasEagerState: false, eagerState: null, next: null };
  if (zi(a)) Ai(b, e);
  else {
    var f2 = a.alternate;
    if (0 === a.lanes && (null === f2 || 0 === f2.lanes) && (f2 = b.lastRenderedReducer, null !== f2)) try {
      var g = b.lastRenderedState, h = f2(g, c);
      e.hasEagerState = true;
      e.eagerState = h;
      if (He(h, g)) {
        var k2 = b.interleaved;
        null === k2 ? (e.next = e, gh(b)) : (e.next = k2.next, k2.next = e);
        b.interleaved = e;
        return;
      }
    } catch (l2) {
    } finally {
    }
    c = hh(a, b, e, d);
    null !== c && (e = R(), gi(c, a, d, e), Bi(c, b, d));
  }
}
function zi(a) {
  var b = a.alternate;
  return a === M || null !== b && b === M;
}
function Ai(a, b) {
  Jh = Ih = true;
  var c = a.pending;
  null === c ? b.next = b : (b.next = c.next, c.next = b);
  a.pending = b;
}
function Bi(a, b, c) {
  if (0 !== (c & 4194240)) {
    var d = b.lanes;
    d &= a.pendingLanes;
    c |= d;
    b.lanes = c;
    Cc(a, c);
  }
}
var Rh = { readContext: eh, useCallback: P, useContext: P, useEffect: P, useImperativeHandle: P, useInsertionEffect: P, useLayoutEffect: P, useMemo: P, useReducer: P, useRef: P, useState: P, useDebugValue: P, useDeferredValue: P, useTransition: P, useMutableSource: P, useSyncExternalStore: P, useId: P, unstable_isNewReconciler: false }, Oh = { readContext: eh, useCallback: function(a, b) {
  Th().memoizedState = [a, void 0 === b ? null : b];
  return a;
}, useContext: eh, useEffect: mi, useImperativeHandle: function(a, b, c) {
  c = null !== c && void 0 !== c ? c.concat([a]) : null;
  return ki(
    4194308,
    4,
    pi.bind(null, b, a),
    c
  );
}, useLayoutEffect: function(a, b) {
  return ki(4194308, 4, a, b);
}, useInsertionEffect: function(a, b) {
  return ki(4, 2, a, b);
}, useMemo: function(a, b) {
  var c = Th();
  b = void 0 === b ? null : b;
  a = a();
  c.memoizedState = [a, b];
  return a;
}, useReducer: function(a, b, c) {
  var d = Th();
  b = void 0 !== c ? c(b) : b;
  d.memoizedState = d.baseState = b;
  a = { pending: null, interleaved: null, lanes: 0, dispatch: null, lastRenderedReducer: a, lastRenderedState: b };
  d.queue = a;
  a = a.dispatch = xi.bind(null, M, a);
  return [d.memoizedState, a];
}, useRef: function(a) {
  var b = Th();
  a = { current: a };
  return b.memoizedState = a;
}, useState: hi, useDebugValue: ri, useDeferredValue: function(a) {
  return Th().memoizedState = a;
}, useTransition: function() {
  var a = hi(false), b = a[0];
  a = vi.bind(null, a[1]);
  Th().memoizedState = a;
  return [b, a];
}, useMutableSource: function() {
}, useSyncExternalStore: function(a, b, c) {
  var d = M, e = Th();
  if (I) {
    if (void 0 === c) throw Error(p(407));
    c = c();
  } else {
    c = b();
    if (null === Q) throw Error(p(349));
    0 !== (Hh & 30) || di(d, b, c);
  }
  e.memoizedState = c;
  var f2 = { value: c, getSnapshot: b };
  e.queue = f2;
  mi(ai.bind(
    null,
    d,
    f2,
    a
  ), [a]);
  d.flags |= 2048;
  bi(9, ci.bind(null, d, f2, c, b), void 0, null);
  return c;
}, useId: function() {
  var a = Th(), b = Q.identifierPrefix;
  if (I) {
    var c = sg;
    var d = rg;
    c = (d & ~(1 << 32 - oc(d) - 1)).toString(32) + c;
    b = ":" + b + "R" + c;
    c = Kh++;
    0 < c && (b += "H" + c.toString(32));
    b += ":";
  } else c = Lh++, b = ":" + b + "r" + c.toString(32) + ":";
  return a.memoizedState = b;
}, unstable_isNewReconciler: false }, Ph = {
  readContext: eh,
  useCallback: si,
  useContext: eh,
  useEffect: $h,
  useImperativeHandle: qi,
  useInsertionEffect: ni,
  useLayoutEffect: oi,
  useMemo: ti,
  useReducer: Wh,
  useRef: ji,
  useState: function() {
    return Wh(Vh);
  },
  useDebugValue: ri,
  useDeferredValue: function(a) {
    var b = Uh();
    return ui(b, N.memoizedState, a);
  },
  useTransition: function() {
    var a = Wh(Vh)[0], b = Uh().memoizedState;
    return [a, b];
  },
  useMutableSource: Yh,
  useSyncExternalStore: Zh,
  useId: wi,
  unstable_isNewReconciler: false
}, Qh = { readContext: eh, useCallback: si, useContext: eh, useEffect: $h, useImperativeHandle: qi, useInsertionEffect: ni, useLayoutEffect: oi, useMemo: ti, useReducer: Xh, useRef: ji, useState: function() {
  return Xh(Vh);
}, useDebugValue: ri, useDeferredValue: function(a) {
  var b = Uh();
  return null === N ? b.memoizedState = a : ui(b, N.memoizedState, a);
}, useTransition: function() {
  var a = Xh(Vh)[0], b = Uh().memoizedState;
  return [a, b];
}, useMutableSource: Yh, useSyncExternalStore: Zh, useId: wi, unstable_isNewReconciler: false };
function Ci(a, b) {
  if (a && a.defaultProps) {
    b = A({}, b);
    a = a.defaultProps;
    for (var c in a) void 0 === b[c] && (b[c] = a[c]);
    return b;
  }
  return b;
}
function Di(a, b, c, d) {
  b = a.memoizedState;
  c = c(d, b);
  c = null === c || void 0 === c ? b : A({}, b, c);
  a.memoizedState = c;
  0 === a.lanes && (a.updateQueue.baseState = c);
}
var Ei = { isMounted: function(a) {
  return (a = a._reactInternals) ? Vb(a) === a : false;
}, enqueueSetState: function(a, b, c) {
  a = a._reactInternals;
  var d = R(), e = yi(a), f2 = mh(d, e);
  f2.payload = b;
  void 0 !== c && null !== c && (f2.callback = c);
  b = nh(a, f2, e);
  null !== b && (gi(b, a, e, d), oh(b, a, e));
}, enqueueReplaceState: function(a, b, c) {
  a = a._reactInternals;
  var d = R(), e = yi(a), f2 = mh(d, e);
  f2.tag = 1;
  f2.payload = b;
  void 0 !== c && null !== c && (f2.callback = c);
  b = nh(a, f2, e);
  null !== b && (gi(b, a, e, d), oh(b, a, e));
}, enqueueForceUpdate: function(a, b) {
  a = a._reactInternals;
  var c = R(), d = yi(a), e = mh(c, d);
  e.tag = 2;
  void 0 !== b && null !== b && (e.callback = b);
  b = nh(a, e, d);
  null !== b && (gi(b, a, d, c), oh(b, a, d));
} };
function Fi(a, b, c, d, e, f2, g) {
  a = a.stateNode;
  return "function" === typeof a.shouldComponentUpdate ? a.shouldComponentUpdate(d, f2, g) : b.prototype && b.prototype.isPureReactComponent ? !Ie(c, d) || !Ie(e, f2) : true;
}
function Gi(a, b, c) {
  var d = false, e = Vf;
  var f2 = b.contextType;
  "object" === typeof f2 && null !== f2 ? f2 = eh(f2) : (e = Zf(b) ? Xf : H.current, d = b.contextTypes, f2 = (d = null !== d && void 0 !== d) ? Yf(a, e) : Vf);
  b = new b(c, f2);
  a.memoizedState = null !== b.state && void 0 !== b.state ? b.state : null;
  b.updater = Ei;
  a.stateNode = b;
  b._reactInternals = a;
  d && (a = a.stateNode, a.__reactInternalMemoizedUnmaskedChildContext = e, a.__reactInternalMemoizedMaskedChildContext = f2);
  return b;
}
function Hi(a, b, c, d) {
  a = b.state;
  "function" === typeof b.componentWillReceiveProps && b.componentWillReceiveProps(c, d);
  "function" === typeof b.UNSAFE_componentWillReceiveProps && b.UNSAFE_componentWillReceiveProps(c, d);
  b.state !== a && Ei.enqueueReplaceState(b, b.state, null);
}
function Ii(a, b, c, d) {
  var e = a.stateNode;
  e.props = c;
  e.state = a.memoizedState;
  e.refs = {};
  kh(a);
  var f2 = b.contextType;
  "object" === typeof f2 && null !== f2 ? e.context = eh(f2) : (f2 = Zf(b) ? Xf : H.current, e.context = Yf(a, f2));
  e.state = a.memoizedState;
  f2 = b.getDerivedStateFromProps;
  "function" === typeof f2 && (Di(a, b, f2, c), e.state = a.memoizedState);
  "function" === typeof b.getDerivedStateFromProps || "function" === typeof e.getSnapshotBeforeUpdate || "function" !== typeof e.UNSAFE_componentWillMount && "function" !== typeof e.componentWillMount || (b = e.state, "function" === typeof e.componentWillMount && e.componentWillMount(), "function" === typeof e.UNSAFE_componentWillMount && e.UNSAFE_componentWillMount(), b !== e.state && Ei.enqueueReplaceState(e, e.state, null), qh(a, c, e, d), e.state = a.memoizedState);
  "function" === typeof e.componentDidMount && (a.flags |= 4194308);
}
function Ji(a, b) {
  try {
    var c = "", d = b;
    do
      c += Pa(d), d = d.return;
    while (d);
    var e = c;
  } catch (f2) {
    e = "\nError generating stack: " + f2.message + "\n" + f2.stack;
  }
  return { value: a, source: b, stack: e, digest: null };
}
function Ki(a, b, c) {
  return { value: a, source: null, stack: null != c ? c : null, digest: null != b ? b : null };
}
function Li(a, b) {
  try {
    console.error(b.value);
  } catch (c) {
    setTimeout(function() {
      throw c;
    });
  }
}
var Mi = "function" === typeof WeakMap ? WeakMap : Map;
function Ni(a, b, c) {
  c = mh(-1, c);
  c.tag = 3;
  c.payload = { element: null };
  var d = b.value;
  c.callback = function() {
    Oi || (Oi = true, Pi = d);
    Li(a, b);
  };
  return c;
}
function Qi(a, b, c) {
  c = mh(-1, c);
  c.tag = 3;
  var d = a.type.getDerivedStateFromError;
  if ("function" === typeof d) {
    var e = b.value;
    c.payload = function() {
      return d(e);
    };
    c.callback = function() {
      Li(a, b);
    };
  }
  var f2 = a.stateNode;
  null !== f2 && "function" === typeof f2.componentDidCatch && (c.callback = function() {
    Li(a, b);
    "function" !== typeof d && (null === Ri ? Ri = /* @__PURE__ */ new Set([this]) : Ri.add(this));
    var c2 = b.stack;
    this.componentDidCatch(b.value, { componentStack: null !== c2 ? c2 : "" });
  });
  return c;
}
function Si(a, b, c) {
  var d = a.pingCache;
  if (null === d) {
    d = a.pingCache = new Mi();
    var e = /* @__PURE__ */ new Set();
    d.set(b, e);
  } else e = d.get(b), void 0 === e && (e = /* @__PURE__ */ new Set(), d.set(b, e));
  e.has(c) || (e.add(c), a = Ti.bind(null, a, b, c), b.then(a, a));
}
function Ui(a) {
  do {
    var b;
    if (b = 13 === a.tag) b = a.memoizedState, b = null !== b ? null !== b.dehydrated ? true : false : true;
    if (b) return a;
    a = a.return;
  } while (null !== a);
  return null;
}
function Vi(a, b, c, d, e) {
  if (0 === (a.mode & 1)) return a === b ? a.flags |= 65536 : (a.flags |= 128, c.flags |= 131072, c.flags &= -52805, 1 === c.tag && (null === c.alternate ? c.tag = 17 : (b = mh(-1, 1), b.tag = 2, nh(c, b, 1))), c.lanes |= 1), a;
  a.flags |= 65536;
  a.lanes = e;
  return a;
}
var Wi = ua.ReactCurrentOwner, dh = false;
function Xi(a, b, c, d) {
  b.child = null === a ? Vg(b, null, c, d) : Ug(b, a.child, c, d);
}
function Yi(a, b, c, d, e) {
  c = c.render;
  var f2 = b.ref;
  ch(b, e);
  d = Nh(a, b, c, d, f2, e);
  c = Sh();
  if (null !== a && !dh) return b.updateQueue = a.updateQueue, b.flags &= -2053, a.lanes &= ~e, Zi(a, b, e);
  I && c && vg(b);
  b.flags |= 1;
  Xi(a, b, d, e);
  return b.child;
}
function $i(a, b, c, d, e) {
  if (null === a) {
    var f2 = c.type;
    if ("function" === typeof f2 && !aj(f2) && void 0 === f2.defaultProps && null === c.compare && void 0 === c.defaultProps) return b.tag = 15, b.type = f2, bj(a, b, f2, d, e);
    a = Rg(c.type, null, d, b, b.mode, e);
    a.ref = b.ref;
    a.return = b;
    return b.child = a;
  }
  f2 = a.child;
  if (0 === (a.lanes & e)) {
    var g = f2.memoizedProps;
    c = c.compare;
    c = null !== c ? c : Ie;
    if (c(g, d) && a.ref === b.ref) return Zi(a, b, e);
  }
  b.flags |= 1;
  a = Pg(f2, d);
  a.ref = b.ref;
  a.return = b;
  return b.child = a;
}
function bj(a, b, c, d, e) {
  if (null !== a) {
    var f2 = a.memoizedProps;
    if (Ie(f2, d) && a.ref === b.ref) if (dh = false, b.pendingProps = d = f2, 0 !== (a.lanes & e)) 0 !== (a.flags & 131072) && (dh = true);
    else return b.lanes = a.lanes, Zi(a, b, e);
  }
  return cj(a, b, c, d, e);
}
function dj(a, b, c) {
  var d = b.pendingProps, e = d.children, f2 = null !== a ? a.memoizedState : null;
  if ("hidden" === d.mode) if (0 === (b.mode & 1)) b.memoizedState = { baseLanes: 0, cachePool: null, transitions: null }, G(ej, fj), fj |= c;
  else {
    if (0 === (c & 1073741824)) return a = null !== f2 ? f2.baseLanes | c : c, b.lanes = b.childLanes = 1073741824, b.memoizedState = { baseLanes: a, cachePool: null, transitions: null }, b.updateQueue = null, G(ej, fj), fj |= a, null;
    b.memoizedState = { baseLanes: 0, cachePool: null, transitions: null };
    d = null !== f2 ? f2.baseLanes : c;
    G(ej, fj);
    fj |= d;
  }
  else null !== f2 ? (d = f2.baseLanes | c, b.memoizedState = null) : d = c, G(ej, fj), fj |= d;
  Xi(a, b, e, c);
  return b.child;
}
function gj(a, b) {
  var c = b.ref;
  if (null === a && null !== c || null !== a && a.ref !== c) b.flags |= 512, b.flags |= 2097152;
}
function cj(a, b, c, d, e) {
  var f2 = Zf(c) ? Xf : H.current;
  f2 = Yf(b, f2);
  ch(b, e);
  c = Nh(a, b, c, d, f2, e);
  d = Sh();
  if (null !== a && !dh) return b.updateQueue = a.updateQueue, b.flags &= -2053, a.lanes &= ~e, Zi(a, b, e);
  I && d && vg(b);
  b.flags |= 1;
  Xi(a, b, c, e);
  return b.child;
}
function hj(a, b, c, d, e) {
  if (Zf(c)) {
    var f2 = true;
    cg(b);
  } else f2 = false;
  ch(b, e);
  if (null === b.stateNode) ij(a, b), Gi(b, c, d), Ii(b, c, d, e), d = true;
  else if (null === a) {
    var g = b.stateNode, h = b.memoizedProps;
    g.props = h;
    var k2 = g.context, l2 = c.contextType;
    "object" === typeof l2 && null !== l2 ? l2 = eh(l2) : (l2 = Zf(c) ? Xf : H.current, l2 = Yf(b, l2));
    var m2 = c.getDerivedStateFromProps, q2 = "function" === typeof m2 || "function" === typeof g.getSnapshotBeforeUpdate;
    q2 || "function" !== typeof g.UNSAFE_componentWillReceiveProps && "function" !== typeof g.componentWillReceiveProps || (h !== d || k2 !== l2) && Hi(b, g, d, l2);
    jh = false;
    var r2 = b.memoizedState;
    g.state = r2;
    qh(b, d, g, e);
    k2 = b.memoizedState;
    h !== d || r2 !== k2 || Wf.current || jh ? ("function" === typeof m2 && (Di(b, c, m2, d), k2 = b.memoizedState), (h = jh || Fi(b, c, h, d, r2, k2, l2)) ? (q2 || "function" !== typeof g.UNSAFE_componentWillMount && "function" !== typeof g.componentWillMount || ("function" === typeof g.componentWillMount && g.componentWillMount(), "function" === typeof g.UNSAFE_componentWillMount && g.UNSAFE_componentWillMount()), "function" === typeof g.componentDidMount && (b.flags |= 4194308)) : ("function" === typeof g.componentDidMount && (b.flags |= 4194308), b.memoizedProps = d, b.memoizedState = k2), g.props = d, g.state = k2, g.context = l2, d = h) : ("function" === typeof g.componentDidMount && (b.flags |= 4194308), d = false);
  } else {
    g = b.stateNode;
    lh(a, b);
    h = b.memoizedProps;
    l2 = b.type === b.elementType ? h : Ci(b.type, h);
    g.props = l2;
    q2 = b.pendingProps;
    r2 = g.context;
    k2 = c.contextType;
    "object" === typeof k2 && null !== k2 ? k2 = eh(k2) : (k2 = Zf(c) ? Xf : H.current, k2 = Yf(b, k2));
    var y2 = c.getDerivedStateFromProps;
    (m2 = "function" === typeof y2 || "function" === typeof g.getSnapshotBeforeUpdate) || "function" !== typeof g.UNSAFE_componentWillReceiveProps && "function" !== typeof g.componentWillReceiveProps || (h !== q2 || r2 !== k2) && Hi(b, g, d, k2);
    jh = false;
    r2 = b.memoizedState;
    g.state = r2;
    qh(b, d, g, e);
    var n2 = b.memoizedState;
    h !== q2 || r2 !== n2 || Wf.current || jh ? ("function" === typeof y2 && (Di(b, c, y2, d), n2 = b.memoizedState), (l2 = jh || Fi(b, c, l2, d, r2, n2, k2) || false) ? (m2 || "function" !== typeof g.UNSAFE_componentWillUpdate && "function" !== typeof g.componentWillUpdate || ("function" === typeof g.componentWillUpdate && g.componentWillUpdate(d, n2, k2), "function" === typeof g.UNSAFE_componentWillUpdate && g.UNSAFE_componentWillUpdate(d, n2, k2)), "function" === typeof g.componentDidUpdate && (b.flags |= 4), "function" === typeof g.getSnapshotBeforeUpdate && (b.flags |= 1024)) : ("function" !== typeof g.componentDidUpdate || h === a.memoizedProps && r2 === a.memoizedState || (b.flags |= 4), "function" !== typeof g.getSnapshotBeforeUpdate || h === a.memoizedProps && r2 === a.memoizedState || (b.flags |= 1024), b.memoizedProps = d, b.memoizedState = n2), g.props = d, g.state = n2, g.context = k2, d = l2) : ("function" !== typeof g.componentDidUpdate || h === a.memoizedProps && r2 === a.memoizedState || (b.flags |= 4), "function" !== typeof g.getSnapshotBeforeUpdate || h === a.memoizedProps && r2 === a.memoizedState || (b.flags |= 1024), d = false);
  }
  return jj(a, b, c, d, f2, e);
}
function jj(a, b, c, d, e, f2) {
  gj(a, b);
  var g = 0 !== (b.flags & 128);
  if (!d && !g) return e && dg(b, c, false), Zi(a, b, f2);
  d = b.stateNode;
  Wi.current = b;
  var h = g && "function" !== typeof c.getDerivedStateFromError ? null : d.render();
  b.flags |= 1;
  null !== a && g ? (b.child = Ug(b, a.child, null, f2), b.child = Ug(b, null, h, f2)) : Xi(a, b, h, f2);
  b.memoizedState = d.state;
  e && dg(b, c, true);
  return b.child;
}
function kj(a) {
  var b = a.stateNode;
  b.pendingContext ? ag(a, b.pendingContext, b.pendingContext !== b.context) : b.context && ag(a, b.context, false);
  yh(a, b.containerInfo);
}
function lj(a, b, c, d, e) {
  Ig();
  Jg(e);
  b.flags |= 256;
  Xi(a, b, c, d);
  return b.child;
}
var mj = { dehydrated: null, treeContext: null, retryLane: 0 };
function nj(a) {
  return { baseLanes: a, cachePool: null, transitions: null };
}
function oj(a, b, c) {
  var d = b.pendingProps, e = L.current, f2 = false, g = 0 !== (b.flags & 128), h;
  (h = g) || (h = null !== a && null === a.memoizedState ? false : 0 !== (e & 2));
  if (h) f2 = true, b.flags &= -129;
  else if (null === a || null !== a.memoizedState) e |= 1;
  G(L, e & 1);
  if (null === a) {
    Eg(b);
    a = b.memoizedState;
    if (null !== a && (a = a.dehydrated, null !== a)) return 0 === (b.mode & 1) ? b.lanes = 1 : "$!" === a.data ? b.lanes = 8 : b.lanes = 1073741824, null;
    g = d.children;
    a = d.fallback;
    return f2 ? (d = b.mode, f2 = b.child, g = { mode: "hidden", children: g }, 0 === (d & 1) && null !== f2 ? (f2.childLanes = 0, f2.pendingProps = g) : f2 = pj(g, d, 0, null), a = Tg(a, d, c, null), f2.return = b, a.return = b, f2.sibling = a, b.child = f2, b.child.memoizedState = nj(c), b.memoizedState = mj, a) : qj(b, g);
  }
  e = a.memoizedState;
  if (null !== e && (h = e.dehydrated, null !== h)) return rj(a, b, g, d, h, e, c);
  if (f2) {
    f2 = d.fallback;
    g = b.mode;
    e = a.child;
    h = e.sibling;
    var k2 = { mode: "hidden", children: d.children };
    0 === (g & 1) && b.child !== e ? (d = b.child, d.childLanes = 0, d.pendingProps = k2, b.deletions = null) : (d = Pg(e, k2), d.subtreeFlags = e.subtreeFlags & 14680064);
    null !== h ? f2 = Pg(h, f2) : (f2 = Tg(f2, g, c, null), f2.flags |= 2);
    f2.return = b;
    d.return = b;
    d.sibling = f2;
    b.child = d;
    d = f2;
    f2 = b.child;
    g = a.child.memoizedState;
    g = null === g ? nj(c) : { baseLanes: g.baseLanes | c, cachePool: null, transitions: g.transitions };
    f2.memoizedState = g;
    f2.childLanes = a.childLanes & ~c;
    b.memoizedState = mj;
    return d;
  }
  f2 = a.child;
  a = f2.sibling;
  d = Pg(f2, { mode: "visible", children: d.children });
  0 === (b.mode & 1) && (d.lanes = c);
  d.return = b;
  d.sibling = null;
  null !== a && (c = b.deletions, null === c ? (b.deletions = [a], b.flags |= 16) : c.push(a));
  b.child = d;
  b.memoizedState = null;
  return d;
}
function qj(a, b) {
  b = pj({ mode: "visible", children: b }, a.mode, 0, null);
  b.return = a;
  return a.child = b;
}
function sj(a, b, c, d) {
  null !== d && Jg(d);
  Ug(b, a.child, null, c);
  a = qj(b, b.pendingProps.children);
  a.flags |= 2;
  b.memoizedState = null;
  return a;
}
function rj(a, b, c, d, e, f2, g) {
  if (c) {
    if (b.flags & 256) return b.flags &= -257, d = Ki(Error(p(422))), sj(a, b, g, d);
    if (null !== b.memoizedState) return b.child = a.child, b.flags |= 128, null;
    f2 = d.fallback;
    e = b.mode;
    d = pj({ mode: "visible", children: d.children }, e, 0, null);
    f2 = Tg(f2, e, g, null);
    f2.flags |= 2;
    d.return = b;
    f2.return = b;
    d.sibling = f2;
    b.child = d;
    0 !== (b.mode & 1) && Ug(b, a.child, null, g);
    b.child.memoizedState = nj(g);
    b.memoizedState = mj;
    return f2;
  }
  if (0 === (b.mode & 1)) return sj(a, b, g, null);
  if ("$!" === e.data) {
    d = e.nextSibling && e.nextSibling.dataset;
    if (d) var h = d.dgst;
    d = h;
    f2 = Error(p(419));
    d = Ki(f2, d, void 0);
    return sj(a, b, g, d);
  }
  h = 0 !== (g & a.childLanes);
  if (dh || h) {
    d = Q;
    if (null !== d) {
      switch (g & -g) {
        case 4:
          e = 2;
          break;
        case 16:
          e = 8;
          break;
        case 64:
        case 128:
        case 256:
        case 512:
        case 1024:
        case 2048:
        case 4096:
        case 8192:
        case 16384:
        case 32768:
        case 65536:
        case 131072:
        case 262144:
        case 524288:
        case 1048576:
        case 2097152:
        case 4194304:
        case 8388608:
        case 16777216:
        case 33554432:
        case 67108864:
          e = 32;
          break;
        case 536870912:
          e = 268435456;
          break;
        default:
          e = 0;
      }
      e = 0 !== (e & (d.suspendedLanes | g)) ? 0 : e;
      0 !== e && e !== f2.retryLane && (f2.retryLane = e, ih(a, e), gi(d, a, e, -1));
    }
    tj();
    d = Ki(Error(p(421)));
    return sj(a, b, g, d);
  }
  if ("$?" === e.data) return b.flags |= 128, b.child = a.child, b = uj.bind(null, a), e._reactRetry = b, null;
  a = f2.treeContext;
  yg = Lf(e.nextSibling);
  xg = b;
  I = true;
  zg = null;
  null !== a && (og[pg++] = rg, og[pg++] = sg, og[pg++] = qg, rg = a.id, sg = a.overflow, qg = b);
  b = qj(b, d.children);
  b.flags |= 4096;
  return b;
}
function vj(a, b, c) {
  a.lanes |= b;
  var d = a.alternate;
  null !== d && (d.lanes |= b);
  bh(a.return, b, c);
}
function wj(a, b, c, d, e) {
  var f2 = a.memoizedState;
  null === f2 ? a.memoizedState = { isBackwards: b, rendering: null, renderingStartTime: 0, last: d, tail: c, tailMode: e } : (f2.isBackwards = b, f2.rendering = null, f2.renderingStartTime = 0, f2.last = d, f2.tail = c, f2.tailMode = e);
}
function xj(a, b, c) {
  var d = b.pendingProps, e = d.revealOrder, f2 = d.tail;
  Xi(a, b, d.children, c);
  d = L.current;
  if (0 !== (d & 2)) d = d & 1 | 2, b.flags |= 128;
  else {
    if (null !== a && 0 !== (a.flags & 128)) a: for (a = b.child; null !== a; ) {
      if (13 === a.tag) null !== a.memoizedState && vj(a, c, b);
      else if (19 === a.tag) vj(a, c, b);
      else if (null !== a.child) {
        a.child.return = a;
        a = a.child;
        continue;
      }
      if (a === b) break a;
      for (; null === a.sibling; ) {
        if (null === a.return || a.return === b) break a;
        a = a.return;
      }
      a.sibling.return = a.return;
      a = a.sibling;
    }
    d &= 1;
  }
  G(L, d);
  if (0 === (b.mode & 1)) b.memoizedState = null;
  else switch (e) {
    case "forwards":
      c = b.child;
      for (e = null; null !== c; ) a = c.alternate, null !== a && null === Ch(a) && (e = c), c = c.sibling;
      c = e;
      null === c ? (e = b.child, b.child = null) : (e = c.sibling, c.sibling = null);
      wj(b, false, e, c, f2);
      break;
    case "backwards":
      c = null;
      e = b.child;
      for (b.child = null; null !== e; ) {
        a = e.alternate;
        if (null !== a && null === Ch(a)) {
          b.child = e;
          break;
        }
        a = e.sibling;
        e.sibling = c;
        c = e;
        e = a;
      }
      wj(b, true, c, null, f2);
      break;
    case "together":
      wj(b, false, null, null, void 0);
      break;
    default:
      b.memoizedState = null;
  }
  return b.child;
}
function ij(a, b) {
  0 === (b.mode & 1) && null !== a && (a.alternate = null, b.alternate = null, b.flags |= 2);
}
function Zi(a, b, c) {
  null !== a && (b.dependencies = a.dependencies);
  rh |= b.lanes;
  if (0 === (c & b.childLanes)) return null;
  if (null !== a && b.child !== a.child) throw Error(p(153));
  if (null !== b.child) {
    a = b.child;
    c = Pg(a, a.pendingProps);
    b.child = c;
    for (c.return = b; null !== a.sibling; ) a = a.sibling, c = c.sibling = Pg(a, a.pendingProps), c.return = b;
    c.sibling = null;
  }
  return b.child;
}
function yj(a, b, c) {
  switch (b.tag) {
    case 3:
      kj(b);
      Ig();
      break;
    case 5:
      Ah(b);
      break;
    case 1:
      Zf(b.type) && cg(b);
      break;
    case 4:
      yh(b, b.stateNode.containerInfo);
      break;
    case 10:
      var d = b.type._context, e = b.memoizedProps.value;
      G(Wg, d._currentValue);
      d._currentValue = e;
      break;
    case 13:
      d = b.memoizedState;
      if (null !== d) {
        if (null !== d.dehydrated) return G(L, L.current & 1), b.flags |= 128, null;
        if (0 !== (c & b.child.childLanes)) return oj(a, b, c);
        G(L, L.current & 1);
        a = Zi(a, b, c);
        return null !== a ? a.sibling : null;
      }
      G(L, L.current & 1);
      break;
    case 19:
      d = 0 !== (c & b.childLanes);
      if (0 !== (a.flags & 128)) {
        if (d) return xj(a, b, c);
        b.flags |= 128;
      }
      e = b.memoizedState;
      null !== e && (e.rendering = null, e.tail = null, e.lastEffect = null);
      G(L, L.current);
      if (d) break;
      else return null;
    case 22:
    case 23:
      return b.lanes = 0, dj(a, b, c);
  }
  return Zi(a, b, c);
}
var zj, Aj, Bj, Cj;
zj = function(a, b) {
  for (var c = b.child; null !== c; ) {
    if (5 === c.tag || 6 === c.tag) a.appendChild(c.stateNode);
    else if (4 !== c.tag && null !== c.child) {
      c.child.return = c;
      c = c.child;
      continue;
    }
    if (c === b) break;
    for (; null === c.sibling; ) {
      if (null === c.return || c.return === b) return;
      c = c.return;
    }
    c.sibling.return = c.return;
    c = c.sibling;
  }
};
Aj = function() {
};
Bj = function(a, b, c, d) {
  var e = a.memoizedProps;
  if (e !== d) {
    a = b.stateNode;
    xh(uh.current);
    var f2 = null;
    switch (c) {
      case "input":
        e = Ya(a, e);
        d = Ya(a, d);
        f2 = [];
        break;
      case "select":
        e = A({}, e, { value: void 0 });
        d = A({}, d, { value: void 0 });
        f2 = [];
        break;
      case "textarea":
        e = gb(a, e);
        d = gb(a, d);
        f2 = [];
        break;
      default:
        "function" !== typeof e.onClick && "function" === typeof d.onClick && (a.onclick = Bf);
    }
    ub(c, d);
    var g;
    c = null;
    for (l2 in e) if (!d.hasOwnProperty(l2) && e.hasOwnProperty(l2) && null != e[l2]) if ("style" === l2) {
      var h = e[l2];
      for (g in h) h.hasOwnProperty(g) && (c || (c = {}), c[g] = "");
    } else "dangerouslySetInnerHTML" !== l2 && "children" !== l2 && "suppressContentEditableWarning" !== l2 && "suppressHydrationWarning" !== l2 && "autoFocus" !== l2 && (ea.hasOwnProperty(l2) ? f2 || (f2 = []) : (f2 = f2 || []).push(l2, null));
    for (l2 in d) {
      var k2 = d[l2];
      h = null != e ? e[l2] : void 0;
      if (d.hasOwnProperty(l2) && k2 !== h && (null != k2 || null != h)) if ("style" === l2) if (h) {
        for (g in h) !h.hasOwnProperty(g) || k2 && k2.hasOwnProperty(g) || (c || (c = {}), c[g] = "");
        for (g in k2) k2.hasOwnProperty(g) && h[g] !== k2[g] && (c || (c = {}), c[g] = k2[g]);
      } else c || (f2 || (f2 = []), f2.push(
        l2,
        c
      )), c = k2;
      else "dangerouslySetInnerHTML" === l2 ? (k2 = k2 ? k2.__html : void 0, h = h ? h.__html : void 0, null != k2 && h !== k2 && (f2 = f2 || []).push(l2, k2)) : "children" === l2 ? "string" !== typeof k2 && "number" !== typeof k2 || (f2 = f2 || []).push(l2, "" + k2) : "suppressContentEditableWarning" !== l2 && "suppressHydrationWarning" !== l2 && (ea.hasOwnProperty(l2) ? (null != k2 && "onScroll" === l2 && D("scroll", a), f2 || h === k2 || (f2 = [])) : (f2 = f2 || []).push(l2, k2));
    }
    c && (f2 = f2 || []).push("style", c);
    var l2 = f2;
    if (b.updateQueue = l2) b.flags |= 4;
  }
};
Cj = function(a, b, c, d) {
  c !== d && (b.flags |= 4);
};
function Dj(a, b) {
  if (!I) switch (a.tailMode) {
    case "hidden":
      b = a.tail;
      for (var c = null; null !== b; ) null !== b.alternate && (c = b), b = b.sibling;
      null === c ? a.tail = null : c.sibling = null;
      break;
    case "collapsed":
      c = a.tail;
      for (var d = null; null !== c; ) null !== c.alternate && (d = c), c = c.sibling;
      null === d ? b || null === a.tail ? a.tail = null : a.tail.sibling = null : d.sibling = null;
  }
}
function S(a) {
  var b = null !== a.alternate && a.alternate.child === a.child, c = 0, d = 0;
  if (b) for (var e = a.child; null !== e; ) c |= e.lanes | e.childLanes, d |= e.subtreeFlags & 14680064, d |= e.flags & 14680064, e.return = a, e = e.sibling;
  else for (e = a.child; null !== e; ) c |= e.lanes | e.childLanes, d |= e.subtreeFlags, d |= e.flags, e.return = a, e = e.sibling;
  a.subtreeFlags |= d;
  a.childLanes = c;
  return b;
}
function Ej(a, b, c) {
  var d = b.pendingProps;
  wg(b);
  switch (b.tag) {
    case 2:
    case 16:
    case 15:
    case 0:
    case 11:
    case 7:
    case 8:
    case 12:
    case 9:
    case 14:
      return S(b), null;
    case 1:
      return Zf(b.type) && $f(), S(b), null;
    case 3:
      d = b.stateNode;
      zh();
      E(Wf);
      E(H);
      Eh();
      d.pendingContext && (d.context = d.pendingContext, d.pendingContext = null);
      if (null === a || null === a.child) Gg(b) ? b.flags |= 4 : null === a || a.memoizedState.isDehydrated && 0 === (b.flags & 256) || (b.flags |= 1024, null !== zg && (Fj(zg), zg = null));
      Aj(a, b);
      S(b);
      return null;
    case 5:
      Bh(b);
      var e = xh(wh.current);
      c = b.type;
      if (null !== a && null != b.stateNode) Bj(a, b, c, d, e), a.ref !== b.ref && (b.flags |= 512, b.flags |= 2097152);
      else {
        if (!d) {
          if (null === b.stateNode) throw Error(p(166));
          S(b);
          return null;
        }
        a = xh(uh.current);
        if (Gg(b)) {
          d = b.stateNode;
          c = b.type;
          var f2 = b.memoizedProps;
          d[Of] = b;
          d[Pf] = f2;
          a = 0 !== (b.mode & 1);
          switch (c) {
            case "dialog":
              D("cancel", d);
              D("close", d);
              break;
            case "iframe":
            case "object":
            case "embed":
              D("load", d);
              break;
            case "video":
            case "audio":
              for (e = 0; e < lf.length; e++) D(lf[e], d);
              break;
            case "source":
              D("error", d);
              break;
            case "img":
            case "image":
            case "link":
              D(
                "error",
                d
              );
              D("load", d);
              break;
            case "details":
              D("toggle", d);
              break;
            case "input":
              Za(d, f2);
              D("invalid", d);
              break;
            case "select":
              d._wrapperState = { wasMultiple: !!f2.multiple };
              D("invalid", d);
              break;
            case "textarea":
              hb(d, f2), D("invalid", d);
          }
          ub(c, f2);
          e = null;
          for (var g in f2) if (f2.hasOwnProperty(g)) {
            var h = f2[g];
            "children" === g ? "string" === typeof h ? d.textContent !== h && (true !== f2.suppressHydrationWarning && Af(d.textContent, h, a), e = ["children", h]) : "number" === typeof h && d.textContent !== "" + h && (true !== f2.suppressHydrationWarning && Af(
              d.textContent,
              h,
              a
            ), e = ["children", "" + h]) : ea.hasOwnProperty(g) && null != h && "onScroll" === g && D("scroll", d);
          }
          switch (c) {
            case "input":
              Va(d);
              db(d, f2, true);
              break;
            case "textarea":
              Va(d);
              jb(d);
              break;
            case "select":
            case "option":
              break;
            default:
              "function" === typeof f2.onClick && (d.onclick = Bf);
          }
          d = e;
          b.updateQueue = d;
          null !== d && (b.flags |= 4);
        } else {
          g = 9 === e.nodeType ? e : e.ownerDocument;
          "http://www.w3.org/1999/xhtml" === a && (a = kb(c));
          "http://www.w3.org/1999/xhtml" === a ? "script" === c ? (a = g.createElement("div"), a.innerHTML = "<script><\/script>", a = a.removeChild(a.firstChild)) : "string" === typeof d.is ? a = g.createElement(c, { is: d.is }) : (a = g.createElement(c), "select" === c && (g = a, d.multiple ? g.multiple = true : d.size && (g.size = d.size))) : a = g.createElementNS(a, c);
          a[Of] = b;
          a[Pf] = d;
          zj(a, b, false, false);
          b.stateNode = a;
          a: {
            g = vb(c, d);
            switch (c) {
              case "dialog":
                D("cancel", a);
                D("close", a);
                e = d;
                break;
              case "iframe":
              case "object":
              case "embed":
                D("load", a);
                e = d;
                break;
              case "video":
              case "audio":
                for (e = 0; e < lf.length; e++) D(lf[e], a);
                e = d;
                break;
              case "source":
                D("error", a);
                e = d;
                break;
              case "img":
              case "image":
              case "link":
                D(
                  "error",
                  a
                );
                D("load", a);
                e = d;
                break;
              case "details":
                D("toggle", a);
                e = d;
                break;
              case "input":
                Za(a, d);
                e = Ya(a, d);
                D("invalid", a);
                break;
              case "option":
                e = d;
                break;
              case "select":
                a._wrapperState = { wasMultiple: !!d.multiple };
                e = A({}, d, { value: void 0 });
                D("invalid", a);
                break;
              case "textarea":
                hb(a, d);
                e = gb(a, d);
                D("invalid", a);
                break;
              default:
                e = d;
            }
            ub(c, e);
            h = e;
            for (f2 in h) if (h.hasOwnProperty(f2)) {
              var k2 = h[f2];
              "style" === f2 ? sb(a, k2) : "dangerouslySetInnerHTML" === f2 ? (k2 = k2 ? k2.__html : void 0, null != k2 && nb(a, k2)) : "children" === f2 ? "string" === typeof k2 ? ("textarea" !== c || "" !== k2) && ob(a, k2) : "number" === typeof k2 && ob(a, "" + k2) : "suppressContentEditableWarning" !== f2 && "suppressHydrationWarning" !== f2 && "autoFocus" !== f2 && (ea.hasOwnProperty(f2) ? null != k2 && "onScroll" === f2 && D("scroll", a) : null != k2 && ta(a, f2, k2, g));
            }
            switch (c) {
              case "input":
                Va(a);
                db(a, d, false);
                break;
              case "textarea":
                Va(a);
                jb(a);
                break;
              case "option":
                null != d.value && a.setAttribute("value", "" + Sa(d.value));
                break;
              case "select":
                a.multiple = !!d.multiple;
                f2 = d.value;
                null != f2 ? fb(a, !!d.multiple, f2, false) : null != d.defaultValue && fb(
                  a,
                  !!d.multiple,
                  d.defaultValue,
                  true
                );
                break;
              default:
                "function" === typeof e.onClick && (a.onclick = Bf);
            }
            switch (c) {
              case "button":
              case "input":
              case "select":
              case "textarea":
                d = !!d.autoFocus;
                break a;
              case "img":
                d = true;
                break a;
              default:
                d = false;
            }
          }
          d && (b.flags |= 4);
        }
        null !== b.ref && (b.flags |= 512, b.flags |= 2097152);
      }
      S(b);
      return null;
    case 6:
      if (a && null != b.stateNode) Cj(a, b, a.memoizedProps, d);
      else {
        if ("string" !== typeof d && null === b.stateNode) throw Error(p(166));
        c = xh(wh.current);
        xh(uh.current);
        if (Gg(b)) {
          d = b.stateNode;
          c = b.memoizedProps;
          d[Of] = b;
          if (f2 = d.nodeValue !== c) {
            if (a = xg, null !== a) switch (a.tag) {
              case 3:
                Af(d.nodeValue, c, 0 !== (a.mode & 1));
                break;
              case 5:
                true !== a.memoizedProps.suppressHydrationWarning && Af(d.nodeValue, c, 0 !== (a.mode & 1));
            }
          }
          f2 && (b.flags |= 4);
        } else d = (9 === c.nodeType ? c : c.ownerDocument).createTextNode(d), d[Of] = b, b.stateNode = d;
      }
      S(b);
      return null;
    case 13:
      E(L);
      d = b.memoizedState;
      if (null === a || null !== a.memoizedState && null !== a.memoizedState.dehydrated) {
        if (I && null !== yg && 0 !== (b.mode & 1) && 0 === (b.flags & 128)) Hg(), Ig(), b.flags |= 98560, f2 = false;
        else if (f2 = Gg(b), null !== d && null !== d.dehydrated) {
          if (null === a) {
            if (!f2) throw Error(p(318));
            f2 = b.memoizedState;
            f2 = null !== f2 ? f2.dehydrated : null;
            if (!f2) throw Error(p(317));
            f2[Of] = b;
          } else Ig(), 0 === (b.flags & 128) && (b.memoizedState = null), b.flags |= 4;
          S(b);
          f2 = false;
        } else null !== zg && (Fj(zg), zg = null), f2 = true;
        if (!f2) return b.flags & 65536 ? b : null;
      }
      if (0 !== (b.flags & 128)) return b.lanes = c, b;
      d = null !== d;
      d !== (null !== a && null !== a.memoizedState) && d && (b.child.flags |= 8192, 0 !== (b.mode & 1) && (null === a || 0 !== (L.current & 1) ? 0 === T && (T = 3) : tj()));
      null !== b.updateQueue && (b.flags |= 4);
      S(b);
      return null;
    case 4:
      return zh(), Aj(a, b), null === a && sf(b.stateNode.containerInfo), S(b), null;
    case 10:
      return ah(b.type._context), S(b), null;
    case 17:
      return Zf(b.type) && $f(), S(b), null;
    case 19:
      E(L);
      f2 = b.memoizedState;
      if (null === f2) return S(b), null;
      d = 0 !== (b.flags & 128);
      g = f2.rendering;
      if (null === g) if (d) Dj(f2, false);
      else {
        if (0 !== T || null !== a && 0 !== (a.flags & 128)) for (a = b.child; null !== a; ) {
          g = Ch(a);
          if (null !== g) {
            b.flags |= 128;
            Dj(f2, false);
            d = g.updateQueue;
            null !== d && (b.updateQueue = d, b.flags |= 4);
            b.subtreeFlags = 0;
            d = c;
            for (c = b.child; null !== c; ) f2 = c, a = d, f2.flags &= 14680066, g = f2.alternate, null === g ? (f2.childLanes = 0, f2.lanes = a, f2.child = null, f2.subtreeFlags = 0, f2.memoizedProps = null, f2.memoizedState = null, f2.updateQueue = null, f2.dependencies = null, f2.stateNode = null) : (f2.childLanes = g.childLanes, f2.lanes = g.lanes, f2.child = g.child, f2.subtreeFlags = 0, f2.deletions = null, f2.memoizedProps = g.memoizedProps, f2.memoizedState = g.memoizedState, f2.updateQueue = g.updateQueue, f2.type = g.type, a = g.dependencies, f2.dependencies = null === a ? null : { lanes: a.lanes, firstContext: a.firstContext }), c = c.sibling;
            G(L, L.current & 1 | 2);
            return b.child;
          }
          a = a.sibling;
        }
        null !== f2.tail && B() > Gj && (b.flags |= 128, d = true, Dj(f2, false), b.lanes = 4194304);
      }
      else {
        if (!d) if (a = Ch(g), null !== a) {
          if (b.flags |= 128, d = true, c = a.updateQueue, null !== c && (b.updateQueue = c, b.flags |= 4), Dj(f2, true), null === f2.tail && "hidden" === f2.tailMode && !g.alternate && !I) return S(b), null;
        } else 2 * B() - f2.renderingStartTime > Gj && 1073741824 !== c && (b.flags |= 128, d = true, Dj(f2, false), b.lanes = 4194304);
        f2.isBackwards ? (g.sibling = b.child, b.child = g) : (c = f2.last, null !== c ? c.sibling = g : b.child = g, f2.last = g);
      }
      if (null !== f2.tail) return b = f2.tail, f2.rendering = b, f2.tail = b.sibling, f2.renderingStartTime = B(), b.sibling = null, c = L.current, G(L, d ? c & 1 | 2 : c & 1), b;
      S(b);
      return null;
    case 22:
    case 23:
      return Hj(), d = null !== b.memoizedState, null !== a && null !== a.memoizedState !== d && (b.flags |= 8192), d && 0 !== (b.mode & 1) ? 0 !== (fj & 1073741824) && (S(b), b.subtreeFlags & 6 && (b.flags |= 8192)) : S(b), null;
    case 24:
      return null;
    case 25:
      return null;
  }
  throw Error(p(156, b.tag));
}
function Ij(a, b) {
  wg(b);
  switch (b.tag) {
    case 1:
      return Zf(b.type) && $f(), a = b.flags, a & 65536 ? (b.flags = a & -65537 | 128, b) : null;
    case 3:
      return zh(), E(Wf), E(H), Eh(), a = b.flags, 0 !== (a & 65536) && 0 === (a & 128) ? (b.flags = a & -65537 | 128, b) : null;
    case 5:
      return Bh(b), null;
    case 13:
      E(L);
      a = b.memoizedState;
      if (null !== a && null !== a.dehydrated) {
        if (null === b.alternate) throw Error(p(340));
        Ig();
      }
      a = b.flags;
      return a & 65536 ? (b.flags = a & -65537 | 128, b) : null;
    case 19:
      return E(L), null;
    case 4:
      return zh(), null;
    case 10:
      return ah(b.type._context), null;
    case 22:
    case 23:
      return Hj(), null;
    case 24:
      return null;
    default:
      return null;
  }
}
var Jj = false, U = false, Kj = "function" === typeof WeakSet ? WeakSet : Set, V = null;
function Lj(a, b) {
  var c = a.ref;
  if (null !== c) if ("function" === typeof c) try {
    c(null);
  } catch (d) {
    W(a, b, d);
  }
  else c.current = null;
}
function Mj(a, b, c) {
  try {
    c();
  } catch (d) {
    W(a, b, d);
  }
}
var Nj = false;
function Oj(a, b) {
  Cf = dd;
  a = Me();
  if (Ne(a)) {
    if ("selectionStart" in a) var c = { start: a.selectionStart, end: a.selectionEnd };
    else a: {
      c = (c = a.ownerDocument) && c.defaultView || window;
      var d = c.getSelection && c.getSelection();
      if (d && 0 !== d.rangeCount) {
        c = d.anchorNode;
        var e = d.anchorOffset, f2 = d.focusNode;
        d = d.focusOffset;
        try {
          c.nodeType, f2.nodeType;
        } catch (F2) {
          c = null;
          break a;
        }
        var g = 0, h = -1, k2 = -1, l2 = 0, m2 = 0, q2 = a, r2 = null;
        b: for (; ; ) {
          for (var y2; ; ) {
            q2 !== c || 0 !== e && 3 !== q2.nodeType || (h = g + e);
            q2 !== f2 || 0 !== d && 3 !== q2.nodeType || (k2 = g + d);
            3 === q2.nodeType && (g += q2.nodeValue.length);
            if (null === (y2 = q2.firstChild)) break;
            r2 = q2;
            q2 = y2;
          }
          for (; ; ) {
            if (q2 === a) break b;
            r2 === c && ++l2 === e && (h = g);
            r2 === f2 && ++m2 === d && (k2 = g);
            if (null !== (y2 = q2.nextSibling)) break;
            q2 = r2;
            r2 = q2.parentNode;
          }
          q2 = y2;
        }
        c = -1 === h || -1 === k2 ? null : { start: h, end: k2 };
      } else c = null;
    }
    c = c || { start: 0, end: 0 };
  } else c = null;
  Df = { focusedElem: a, selectionRange: c };
  dd = false;
  for (V = b; null !== V; ) if (b = V, a = b.child, 0 !== (b.subtreeFlags & 1028) && null !== a) a.return = b, V = a;
  else for (; null !== V; ) {
    b = V;
    try {
      var n2 = b.alternate;
      if (0 !== (b.flags & 1024)) switch (b.tag) {
        case 0:
        case 11:
        case 15:
          break;
        case 1:
          if (null !== n2) {
            var t2 = n2.memoizedProps, J2 = n2.memoizedState, x2 = b.stateNode, w2 = x2.getSnapshotBeforeUpdate(b.elementType === b.type ? t2 : Ci(b.type, t2), J2);
            x2.__reactInternalSnapshotBeforeUpdate = w2;
          }
          break;
        case 3:
          var u2 = b.stateNode.containerInfo;
          1 === u2.nodeType ? u2.textContent = "" : 9 === u2.nodeType && u2.documentElement && u2.removeChild(u2.documentElement);
          break;
        case 5:
        case 6:
        case 4:
        case 17:
          break;
        default:
          throw Error(p(163));
      }
    } catch (F2) {
      W(b, b.return, F2);
    }
    a = b.sibling;
    if (null !== a) {
      a.return = b.return;
      V = a;
      break;
    }
    V = b.return;
  }
  n2 = Nj;
  Nj = false;
  return n2;
}
function Pj(a, b, c) {
  var d = b.updateQueue;
  d = null !== d ? d.lastEffect : null;
  if (null !== d) {
    var e = d = d.next;
    do {
      if ((e.tag & a) === a) {
        var f2 = e.destroy;
        e.destroy = void 0;
        void 0 !== f2 && Mj(b, c, f2);
      }
      e = e.next;
    } while (e !== d);
  }
}
function Qj(a, b) {
  b = b.updateQueue;
  b = null !== b ? b.lastEffect : null;
  if (null !== b) {
    var c = b = b.next;
    do {
      if ((c.tag & a) === a) {
        var d = c.create;
        c.destroy = d();
      }
      c = c.next;
    } while (c !== b);
  }
}
function Rj(a) {
  var b = a.ref;
  if (null !== b) {
    var c = a.stateNode;
    switch (a.tag) {
      case 5:
        a = c;
        break;
      default:
        a = c;
    }
    "function" === typeof b ? b(a) : b.current = a;
  }
}
function Sj(a) {
  var b = a.alternate;
  null !== b && (a.alternate = null, Sj(b));
  a.child = null;
  a.deletions = null;
  a.sibling = null;
  5 === a.tag && (b = a.stateNode, null !== b && (delete b[Of], delete b[Pf], delete b[of], delete b[Qf], delete b[Rf]));
  a.stateNode = null;
  a.return = null;
  a.dependencies = null;
  a.memoizedProps = null;
  a.memoizedState = null;
  a.pendingProps = null;
  a.stateNode = null;
  a.updateQueue = null;
}
function Tj(a) {
  return 5 === a.tag || 3 === a.tag || 4 === a.tag;
}
function Uj(a) {
  a: for (; ; ) {
    for (; null === a.sibling; ) {
      if (null === a.return || Tj(a.return)) return null;
      a = a.return;
    }
    a.sibling.return = a.return;
    for (a = a.sibling; 5 !== a.tag && 6 !== a.tag && 18 !== a.tag; ) {
      if (a.flags & 2) continue a;
      if (null === a.child || 4 === a.tag) continue a;
      else a.child.return = a, a = a.child;
    }
    if (!(a.flags & 2)) return a.stateNode;
  }
}
function Vj(a, b, c) {
  var d = a.tag;
  if (5 === d || 6 === d) a = a.stateNode, b ? 8 === c.nodeType ? c.parentNode.insertBefore(a, b) : c.insertBefore(a, b) : (8 === c.nodeType ? (b = c.parentNode, b.insertBefore(a, c)) : (b = c, b.appendChild(a)), c = c._reactRootContainer, null !== c && void 0 !== c || null !== b.onclick || (b.onclick = Bf));
  else if (4 !== d && (a = a.child, null !== a)) for (Vj(a, b, c), a = a.sibling; null !== a; ) Vj(a, b, c), a = a.sibling;
}
function Wj(a, b, c) {
  var d = a.tag;
  if (5 === d || 6 === d) a = a.stateNode, b ? c.insertBefore(a, b) : c.appendChild(a);
  else if (4 !== d && (a = a.child, null !== a)) for (Wj(a, b, c), a = a.sibling; null !== a; ) Wj(a, b, c), a = a.sibling;
}
var X = null, Xj = false;
function Yj(a, b, c) {
  for (c = c.child; null !== c; ) Zj(a, b, c), c = c.sibling;
}
function Zj(a, b, c) {
  if (lc && "function" === typeof lc.onCommitFiberUnmount) try {
    lc.onCommitFiberUnmount(kc, c);
  } catch (h) {
  }
  switch (c.tag) {
    case 5:
      U || Lj(c, b);
    case 6:
      var d = X, e = Xj;
      X = null;
      Yj(a, b, c);
      X = d;
      Xj = e;
      null !== X && (Xj ? (a = X, c = c.stateNode, 8 === a.nodeType ? a.parentNode.removeChild(c) : a.removeChild(c)) : X.removeChild(c.stateNode));
      break;
    case 18:
      null !== X && (Xj ? (a = X, c = c.stateNode, 8 === a.nodeType ? Kf(a.parentNode, c) : 1 === a.nodeType && Kf(a, c), bd(a)) : Kf(X, c.stateNode));
      break;
    case 4:
      d = X;
      e = Xj;
      X = c.stateNode.containerInfo;
      Xj = true;
      Yj(a, b, c);
      X = d;
      Xj = e;
      break;
    case 0:
    case 11:
    case 14:
    case 15:
      if (!U && (d = c.updateQueue, null !== d && (d = d.lastEffect, null !== d))) {
        e = d = d.next;
        do {
          var f2 = e, g = f2.destroy;
          f2 = f2.tag;
          void 0 !== g && (0 !== (f2 & 2) ? Mj(c, b, g) : 0 !== (f2 & 4) && Mj(c, b, g));
          e = e.next;
        } while (e !== d);
      }
      Yj(a, b, c);
      break;
    case 1:
      if (!U && (Lj(c, b), d = c.stateNode, "function" === typeof d.componentWillUnmount)) try {
        d.props = c.memoizedProps, d.state = c.memoizedState, d.componentWillUnmount();
      } catch (h) {
        W(c, b, h);
      }
      Yj(a, b, c);
      break;
    case 21:
      Yj(a, b, c);
      break;
    case 22:
      c.mode & 1 ? (U = (d = U) || null !== c.memoizedState, Yj(a, b, c), U = d) : Yj(a, b, c);
      break;
    default:
      Yj(a, b, c);
  }
}
function ak(a) {
  var b = a.updateQueue;
  if (null !== b) {
    a.updateQueue = null;
    var c = a.stateNode;
    null === c && (c = a.stateNode = new Kj());
    b.forEach(function(b2) {
      var d = bk.bind(null, a, b2);
      c.has(b2) || (c.add(b2), b2.then(d, d));
    });
  }
}
function ck(a, b) {
  var c = b.deletions;
  if (null !== c) for (var d = 0; d < c.length; d++) {
    var e = c[d];
    try {
      var f2 = a, g = b, h = g;
      a: for (; null !== h; ) {
        switch (h.tag) {
          case 5:
            X = h.stateNode;
            Xj = false;
            break a;
          case 3:
            X = h.stateNode.containerInfo;
            Xj = true;
            break a;
          case 4:
            X = h.stateNode.containerInfo;
            Xj = true;
            break a;
        }
        h = h.return;
      }
      if (null === X) throw Error(p(160));
      Zj(f2, g, e);
      X = null;
      Xj = false;
      var k2 = e.alternate;
      null !== k2 && (k2.return = null);
      e.return = null;
    } catch (l2) {
      W(e, b, l2);
    }
  }
  if (b.subtreeFlags & 12854) for (b = b.child; null !== b; ) dk(b, a), b = b.sibling;
}
function dk(a, b) {
  var c = a.alternate, d = a.flags;
  switch (a.tag) {
    case 0:
    case 11:
    case 14:
    case 15:
      ck(b, a);
      ek(a);
      if (d & 4) {
        try {
          Pj(3, a, a.return), Qj(3, a);
        } catch (t2) {
          W(a, a.return, t2);
        }
        try {
          Pj(5, a, a.return);
        } catch (t2) {
          W(a, a.return, t2);
        }
      }
      break;
    case 1:
      ck(b, a);
      ek(a);
      d & 512 && null !== c && Lj(c, c.return);
      break;
    case 5:
      ck(b, a);
      ek(a);
      d & 512 && null !== c && Lj(c, c.return);
      if (a.flags & 32) {
        var e = a.stateNode;
        try {
          ob(e, "");
        } catch (t2) {
          W(a, a.return, t2);
        }
      }
      if (d & 4 && (e = a.stateNode, null != e)) {
        var f2 = a.memoizedProps, g = null !== c ? c.memoizedProps : f2, h = a.type, k2 = a.updateQueue;
        a.updateQueue = null;
        if (null !== k2) try {
          "input" === h && "radio" === f2.type && null != f2.name && ab(e, f2);
          vb(h, g);
          var l2 = vb(h, f2);
          for (g = 0; g < k2.length; g += 2) {
            var m2 = k2[g], q2 = k2[g + 1];
            "style" === m2 ? sb(e, q2) : "dangerouslySetInnerHTML" === m2 ? nb(e, q2) : "children" === m2 ? ob(e, q2) : ta(e, m2, q2, l2);
          }
          switch (h) {
            case "input":
              bb(e, f2);
              break;
            case "textarea":
              ib(e, f2);
              break;
            case "select":
              var r2 = e._wrapperState.wasMultiple;
              e._wrapperState.wasMultiple = !!f2.multiple;
              var y2 = f2.value;
              null != y2 ? fb(e, !!f2.multiple, y2, false) : r2 !== !!f2.multiple && (null != f2.defaultValue ? fb(
                e,
                !!f2.multiple,
                f2.defaultValue,
                true
              ) : fb(e, !!f2.multiple, f2.multiple ? [] : "", false));
          }
          e[Pf] = f2;
        } catch (t2) {
          W(a, a.return, t2);
        }
      }
      break;
    case 6:
      ck(b, a);
      ek(a);
      if (d & 4) {
        if (null === a.stateNode) throw Error(p(162));
        e = a.stateNode;
        f2 = a.memoizedProps;
        try {
          e.nodeValue = f2;
        } catch (t2) {
          W(a, a.return, t2);
        }
      }
      break;
    case 3:
      ck(b, a);
      ek(a);
      if (d & 4 && null !== c && c.memoizedState.isDehydrated) try {
        bd(b.containerInfo);
      } catch (t2) {
        W(a, a.return, t2);
      }
      break;
    case 4:
      ck(b, a);
      ek(a);
      break;
    case 13:
      ck(b, a);
      ek(a);
      e = a.child;
      e.flags & 8192 && (f2 = null !== e.memoizedState, e.stateNode.isHidden = f2, !f2 || null !== e.alternate && null !== e.alternate.memoizedState || (fk = B()));
      d & 4 && ak(a);
      break;
    case 22:
      m2 = null !== c && null !== c.memoizedState;
      a.mode & 1 ? (U = (l2 = U) || m2, ck(b, a), U = l2) : ck(b, a);
      ek(a);
      if (d & 8192) {
        l2 = null !== a.memoizedState;
        if ((a.stateNode.isHidden = l2) && !m2 && 0 !== (a.mode & 1)) for (V = a, m2 = a.child; null !== m2; ) {
          for (q2 = V = m2; null !== V; ) {
            r2 = V;
            y2 = r2.child;
            switch (r2.tag) {
              case 0:
              case 11:
              case 14:
              case 15:
                Pj(4, r2, r2.return);
                break;
              case 1:
                Lj(r2, r2.return);
                var n2 = r2.stateNode;
                if ("function" === typeof n2.componentWillUnmount) {
                  d = r2;
                  c = r2.return;
                  try {
                    b = d, n2.props = b.memoizedProps, n2.state = b.memoizedState, n2.componentWillUnmount();
                  } catch (t2) {
                    W(d, c, t2);
                  }
                }
                break;
              case 5:
                Lj(r2, r2.return);
                break;
              case 22:
                if (null !== r2.memoizedState) {
                  gk(q2);
                  continue;
                }
            }
            null !== y2 ? (y2.return = r2, V = y2) : gk(q2);
          }
          m2 = m2.sibling;
        }
        a: for (m2 = null, q2 = a; ; ) {
          if (5 === q2.tag) {
            if (null === m2) {
              m2 = q2;
              try {
                e = q2.stateNode, l2 ? (f2 = e.style, "function" === typeof f2.setProperty ? f2.setProperty("display", "none", "important") : f2.display = "none") : (h = q2.stateNode, k2 = q2.memoizedProps.style, g = void 0 !== k2 && null !== k2 && k2.hasOwnProperty("display") ? k2.display : null, h.style.display = rb("display", g));
              } catch (t2) {
                W(a, a.return, t2);
              }
            }
          } else if (6 === q2.tag) {
            if (null === m2) try {
              q2.stateNode.nodeValue = l2 ? "" : q2.memoizedProps;
            } catch (t2) {
              W(a, a.return, t2);
            }
          } else if ((22 !== q2.tag && 23 !== q2.tag || null === q2.memoizedState || q2 === a) && null !== q2.child) {
            q2.child.return = q2;
            q2 = q2.child;
            continue;
          }
          if (q2 === a) break a;
          for (; null === q2.sibling; ) {
            if (null === q2.return || q2.return === a) break a;
            m2 === q2 && (m2 = null);
            q2 = q2.return;
          }
          m2 === q2 && (m2 = null);
          q2.sibling.return = q2.return;
          q2 = q2.sibling;
        }
      }
      break;
    case 19:
      ck(b, a);
      ek(a);
      d & 4 && ak(a);
      break;
    case 21:
      break;
    default:
      ck(
        b,
        a
      ), ek(a);
  }
}
function ek(a) {
  var b = a.flags;
  if (b & 2) {
    try {
      a: {
        for (var c = a.return; null !== c; ) {
          if (Tj(c)) {
            var d = c;
            break a;
          }
          c = c.return;
        }
        throw Error(p(160));
      }
      switch (d.tag) {
        case 5:
          var e = d.stateNode;
          d.flags & 32 && (ob(e, ""), d.flags &= -33);
          var f2 = Uj(a);
          Wj(a, f2, e);
          break;
        case 3:
        case 4:
          var g = d.stateNode.containerInfo, h = Uj(a);
          Vj(a, h, g);
          break;
        default:
          throw Error(p(161));
      }
    } catch (k2) {
      W(a, a.return, k2);
    }
    a.flags &= -3;
  }
  b & 4096 && (a.flags &= -4097);
}
function hk(a, b, c) {
  V = a;
  ik(a);
}
function ik(a, b, c) {
  for (var d = 0 !== (a.mode & 1); null !== V; ) {
    var e = V, f2 = e.child;
    if (22 === e.tag && d) {
      var g = null !== e.memoizedState || Jj;
      if (!g) {
        var h = e.alternate, k2 = null !== h && null !== h.memoizedState || U;
        h = Jj;
        var l2 = U;
        Jj = g;
        if ((U = k2) && !l2) for (V = e; null !== V; ) g = V, k2 = g.child, 22 === g.tag && null !== g.memoizedState ? jk(e) : null !== k2 ? (k2.return = g, V = k2) : jk(e);
        for (; null !== f2; ) V = f2, ik(f2), f2 = f2.sibling;
        V = e;
        Jj = h;
        U = l2;
      }
      kk(a);
    } else 0 !== (e.subtreeFlags & 8772) && null !== f2 ? (f2.return = e, V = f2) : kk(a);
  }
}
function kk(a) {
  for (; null !== V; ) {
    var b = V;
    if (0 !== (b.flags & 8772)) {
      var c = b.alternate;
      try {
        if (0 !== (b.flags & 8772)) switch (b.tag) {
          case 0:
          case 11:
          case 15:
            U || Qj(5, b);
            break;
          case 1:
            var d = b.stateNode;
            if (b.flags & 4 && !U) if (null === c) d.componentDidMount();
            else {
              var e = b.elementType === b.type ? c.memoizedProps : Ci(b.type, c.memoizedProps);
              d.componentDidUpdate(e, c.memoizedState, d.__reactInternalSnapshotBeforeUpdate);
            }
            var f2 = b.updateQueue;
            null !== f2 && sh(b, f2, d);
            break;
          case 3:
            var g = b.updateQueue;
            if (null !== g) {
              c = null;
              if (null !== b.child) switch (b.child.tag) {
                case 5:
                  c = b.child.stateNode;
                  break;
                case 1:
                  c = b.child.stateNode;
              }
              sh(b, g, c);
            }
            break;
          case 5:
            var h = b.stateNode;
            if (null === c && b.flags & 4) {
              c = h;
              var k2 = b.memoizedProps;
              switch (b.type) {
                case "button":
                case "input":
                case "select":
                case "textarea":
                  k2.autoFocus && c.focus();
                  break;
                case "img":
                  k2.src && (c.src = k2.src);
              }
            }
            break;
          case 6:
            break;
          case 4:
            break;
          case 12:
            break;
          case 13:
            if (null === b.memoizedState) {
              var l2 = b.alternate;
              if (null !== l2) {
                var m2 = l2.memoizedState;
                if (null !== m2) {
                  var q2 = m2.dehydrated;
                  null !== q2 && bd(q2);
                }
              }
            }
            break;
          case 19:
          case 17:
          case 21:
          case 22:
          case 23:
          case 25:
            break;
          default:
            throw Error(p(163));
        }
        U || b.flags & 512 && Rj(b);
      } catch (r2) {
        W(b, b.return, r2);
      }
    }
    if (b === a) {
      V = null;
      break;
    }
    c = b.sibling;
    if (null !== c) {
      c.return = b.return;
      V = c;
      break;
    }
    V = b.return;
  }
}
function gk(a) {
  for (; null !== V; ) {
    var b = V;
    if (b === a) {
      V = null;
      break;
    }
    var c = b.sibling;
    if (null !== c) {
      c.return = b.return;
      V = c;
      break;
    }
    V = b.return;
  }
}
function jk(a) {
  for (; null !== V; ) {
    var b = V;
    try {
      switch (b.tag) {
        case 0:
        case 11:
        case 15:
          var c = b.return;
          try {
            Qj(4, b);
          } catch (k2) {
            W(b, c, k2);
          }
          break;
        case 1:
          var d = b.stateNode;
          if ("function" === typeof d.componentDidMount) {
            var e = b.return;
            try {
              d.componentDidMount();
            } catch (k2) {
              W(b, e, k2);
            }
          }
          var f2 = b.return;
          try {
            Rj(b);
          } catch (k2) {
            W(b, f2, k2);
          }
          break;
        case 5:
          var g = b.return;
          try {
            Rj(b);
          } catch (k2) {
            W(b, g, k2);
          }
      }
    } catch (k2) {
      W(b, b.return, k2);
    }
    if (b === a) {
      V = null;
      break;
    }
    var h = b.sibling;
    if (null !== h) {
      h.return = b.return;
      V = h;
      break;
    }
    V = b.return;
  }
}
var lk = Math.ceil, mk = ua.ReactCurrentDispatcher, nk = ua.ReactCurrentOwner, ok = ua.ReactCurrentBatchConfig, K = 0, Q = null, Y = null, Z = 0, fj = 0, ej = Uf(0), T = 0, pk = null, rh = 0, qk = 0, rk = 0, sk = null, tk = null, fk = 0, Gj = Infinity, uk = null, Oi = false, Pi = null, Ri = null, vk = false, wk = null, xk = 0, yk = 0, zk = null, Ak = -1, Bk = 0;
function R() {
  return 0 !== (K & 6) ? B() : -1 !== Ak ? Ak : Ak = B();
}
function yi(a) {
  if (0 === (a.mode & 1)) return 1;
  if (0 !== (K & 2) && 0 !== Z) return Z & -Z;
  if (null !== Kg.transition) return 0 === Bk && (Bk = yc()), Bk;
  a = C;
  if (0 !== a) return a;
  a = window.event;
  a = void 0 === a ? 16 : jd(a.type);
  return a;
}
function gi(a, b, c, d) {
  if (50 < yk) throw yk = 0, zk = null, Error(p(185));
  Ac(a, c, d);
  if (0 === (K & 2) || a !== Q) a === Q && (0 === (K & 2) && (qk |= c), 4 === T && Ck(a, Z)), Dk(a, d), 1 === c && 0 === K && 0 === (b.mode & 1) && (Gj = B() + 500, fg && jg());
}
function Dk(a, b) {
  var c = a.callbackNode;
  wc(a, b);
  var d = uc(a, a === Q ? Z : 0);
  if (0 === d) null !== c && bc(c), a.callbackNode = null, a.callbackPriority = 0;
  else if (b = d & -d, a.callbackPriority !== b) {
    null != c && bc(c);
    if (1 === b) 0 === a.tag ? ig(Ek.bind(null, a)) : hg(Ek.bind(null, a)), Jf(function() {
      0 === (K & 6) && jg();
    }), c = null;
    else {
      switch (Dc(d)) {
        case 1:
          c = fc;
          break;
        case 4:
          c = gc;
          break;
        case 16:
          c = hc;
          break;
        case 536870912:
          c = jc;
          break;
        default:
          c = hc;
      }
      c = Fk(c, Gk.bind(null, a));
    }
    a.callbackPriority = b;
    a.callbackNode = c;
  }
}
function Gk(a, b) {
  Ak = -1;
  Bk = 0;
  if (0 !== (K & 6)) throw Error(p(327));
  var c = a.callbackNode;
  if (Hk() && a.callbackNode !== c) return null;
  var d = uc(a, a === Q ? Z : 0);
  if (0 === d) return null;
  if (0 !== (d & 30) || 0 !== (d & a.expiredLanes) || b) b = Ik(a, d);
  else {
    b = d;
    var e = K;
    K |= 2;
    var f2 = Jk();
    if (Q !== a || Z !== b) uk = null, Gj = B() + 500, Kk(a, b);
    do
      try {
        Lk();
        break;
      } catch (h) {
        Mk(a, h);
      }
    while (1);
    $g();
    mk.current = f2;
    K = e;
    null !== Y ? b = 0 : (Q = null, Z = 0, b = T);
  }
  if (0 !== b) {
    2 === b && (e = xc(a), 0 !== e && (d = e, b = Nk(a, e)));
    if (1 === b) throw c = pk, Kk(a, 0), Ck(a, d), Dk(a, B()), c;
    if (6 === b) Ck(a, d);
    else {
      e = a.current.alternate;
      if (0 === (d & 30) && !Ok(e) && (b = Ik(a, d), 2 === b && (f2 = xc(a), 0 !== f2 && (d = f2, b = Nk(a, f2))), 1 === b)) throw c = pk, Kk(a, 0), Ck(a, d), Dk(a, B()), c;
      a.finishedWork = e;
      a.finishedLanes = d;
      switch (b) {
        case 0:
        case 1:
          throw Error(p(345));
        case 2:
          Pk(a, tk, uk);
          break;
        case 3:
          Ck(a, d);
          if ((d & 130023424) === d && (b = fk + 500 - B(), 10 < b)) {
            if (0 !== uc(a, 0)) break;
            e = a.suspendedLanes;
            if ((e & d) !== d) {
              R();
              a.pingedLanes |= a.suspendedLanes & e;
              break;
            }
            a.timeoutHandle = Ff(Pk.bind(null, a, tk, uk), b);
            break;
          }
          Pk(a, tk, uk);
          break;
        case 4:
          Ck(a, d);
          if ((d & 4194240) === d) break;
          b = a.eventTimes;
          for (e = -1; 0 < d; ) {
            var g = 31 - oc(d);
            f2 = 1 << g;
            g = b[g];
            g > e && (e = g);
            d &= ~f2;
          }
          d = e;
          d = B() - d;
          d = (120 > d ? 120 : 480 > d ? 480 : 1080 > d ? 1080 : 1920 > d ? 1920 : 3e3 > d ? 3e3 : 4320 > d ? 4320 : 1960 * lk(d / 1960)) - d;
          if (10 < d) {
            a.timeoutHandle = Ff(Pk.bind(null, a, tk, uk), d);
            break;
          }
          Pk(a, tk, uk);
          break;
        case 5:
          Pk(a, tk, uk);
          break;
        default:
          throw Error(p(329));
      }
    }
  }
  Dk(a, B());
  return a.callbackNode === c ? Gk.bind(null, a) : null;
}
function Nk(a, b) {
  var c = sk;
  a.current.memoizedState.isDehydrated && (Kk(a, b).flags |= 256);
  a = Ik(a, b);
  2 !== a && (b = tk, tk = c, null !== b && Fj(b));
  return a;
}
function Fj(a) {
  null === tk ? tk = a : tk.push.apply(tk, a);
}
function Ok(a) {
  for (var b = a; ; ) {
    if (b.flags & 16384) {
      var c = b.updateQueue;
      if (null !== c && (c = c.stores, null !== c)) for (var d = 0; d < c.length; d++) {
        var e = c[d], f2 = e.getSnapshot;
        e = e.value;
        try {
          if (!He(f2(), e)) return false;
        } catch (g) {
          return false;
        }
      }
    }
    c = b.child;
    if (b.subtreeFlags & 16384 && null !== c) c.return = b, b = c;
    else {
      if (b === a) break;
      for (; null === b.sibling; ) {
        if (null === b.return || b.return === a) return true;
        b = b.return;
      }
      b.sibling.return = b.return;
      b = b.sibling;
    }
  }
  return true;
}
function Ck(a, b) {
  b &= ~rk;
  b &= ~qk;
  a.suspendedLanes |= b;
  a.pingedLanes &= ~b;
  for (a = a.expirationTimes; 0 < b; ) {
    var c = 31 - oc(b), d = 1 << c;
    a[c] = -1;
    b &= ~d;
  }
}
function Ek(a) {
  if (0 !== (K & 6)) throw Error(p(327));
  Hk();
  var b = uc(a, 0);
  if (0 === (b & 1)) return Dk(a, B()), null;
  var c = Ik(a, b);
  if (0 !== a.tag && 2 === c) {
    var d = xc(a);
    0 !== d && (b = d, c = Nk(a, d));
  }
  if (1 === c) throw c = pk, Kk(a, 0), Ck(a, b), Dk(a, B()), c;
  if (6 === c) throw Error(p(345));
  a.finishedWork = a.current.alternate;
  a.finishedLanes = b;
  Pk(a, tk, uk);
  Dk(a, B());
  return null;
}
function Qk(a, b) {
  var c = K;
  K |= 1;
  try {
    return a(b);
  } finally {
    K = c, 0 === K && (Gj = B() + 500, fg && jg());
  }
}
function Rk(a) {
  null !== wk && 0 === wk.tag && 0 === (K & 6) && Hk();
  var b = K;
  K |= 1;
  var c = ok.transition, d = C;
  try {
    if (ok.transition = null, C = 1, a) return a();
  } finally {
    C = d, ok.transition = c, K = b, 0 === (K & 6) && jg();
  }
}
function Hj() {
  fj = ej.current;
  E(ej);
}
function Kk(a, b) {
  a.finishedWork = null;
  a.finishedLanes = 0;
  var c = a.timeoutHandle;
  -1 !== c && (a.timeoutHandle = -1, Gf(c));
  if (null !== Y) for (c = Y.return; null !== c; ) {
    var d = c;
    wg(d);
    switch (d.tag) {
      case 1:
        d = d.type.childContextTypes;
        null !== d && void 0 !== d && $f();
        break;
      case 3:
        zh();
        E(Wf);
        E(H);
        Eh();
        break;
      case 5:
        Bh(d);
        break;
      case 4:
        zh();
        break;
      case 13:
        E(L);
        break;
      case 19:
        E(L);
        break;
      case 10:
        ah(d.type._context);
        break;
      case 22:
      case 23:
        Hj();
    }
    c = c.return;
  }
  Q = a;
  Y = a = Pg(a.current, null);
  Z = fj = b;
  T = 0;
  pk = null;
  rk = qk = rh = 0;
  tk = sk = null;
  if (null !== fh) {
    for (b = 0; b < fh.length; b++) if (c = fh[b], d = c.interleaved, null !== d) {
      c.interleaved = null;
      var e = d.next, f2 = c.pending;
      if (null !== f2) {
        var g = f2.next;
        f2.next = e;
        d.next = g;
      }
      c.pending = d;
    }
    fh = null;
  }
  return a;
}
function Mk(a, b) {
  do {
    var c = Y;
    try {
      $g();
      Fh.current = Rh;
      if (Ih) {
        for (var d = M.memoizedState; null !== d; ) {
          var e = d.queue;
          null !== e && (e.pending = null);
          d = d.next;
        }
        Ih = false;
      }
      Hh = 0;
      O = N = M = null;
      Jh = false;
      Kh = 0;
      nk.current = null;
      if (null === c || null === c.return) {
        T = 1;
        pk = b;
        Y = null;
        break;
      }
      a: {
        var f2 = a, g = c.return, h = c, k2 = b;
        b = Z;
        h.flags |= 32768;
        if (null !== k2 && "object" === typeof k2 && "function" === typeof k2.then) {
          var l2 = k2, m2 = h, q2 = m2.tag;
          if (0 === (m2.mode & 1) && (0 === q2 || 11 === q2 || 15 === q2)) {
            var r2 = m2.alternate;
            r2 ? (m2.updateQueue = r2.updateQueue, m2.memoizedState = r2.memoizedState, m2.lanes = r2.lanes) : (m2.updateQueue = null, m2.memoizedState = null);
          }
          var y2 = Ui(g);
          if (null !== y2) {
            y2.flags &= -257;
            Vi(y2, g, h, f2, b);
            y2.mode & 1 && Si(f2, l2, b);
            b = y2;
            k2 = l2;
            var n2 = b.updateQueue;
            if (null === n2) {
              var t2 = /* @__PURE__ */ new Set();
              t2.add(k2);
              b.updateQueue = t2;
            } else n2.add(k2);
            break a;
          } else {
            if (0 === (b & 1)) {
              Si(f2, l2, b);
              tj();
              break a;
            }
            k2 = Error(p(426));
          }
        } else if (I && h.mode & 1) {
          var J2 = Ui(g);
          if (null !== J2) {
            0 === (J2.flags & 65536) && (J2.flags |= 256);
            Vi(J2, g, h, f2, b);
            Jg(Ji(k2, h));
            break a;
          }
        }
        f2 = k2 = Ji(k2, h);
        4 !== T && (T = 2);
        null === sk ? sk = [f2] : sk.push(f2);
        f2 = g;
        do {
          switch (f2.tag) {
            case 3:
              f2.flags |= 65536;
              b &= -b;
              f2.lanes |= b;
              var x2 = Ni(f2, k2, b);
              ph(f2, x2);
              break a;
            case 1:
              h = k2;
              var w2 = f2.type, u2 = f2.stateNode;
              if (0 === (f2.flags & 128) && ("function" === typeof w2.getDerivedStateFromError || null !== u2 && "function" === typeof u2.componentDidCatch && (null === Ri || !Ri.has(u2)))) {
                f2.flags |= 65536;
                b &= -b;
                f2.lanes |= b;
                var F2 = Qi(f2, h, b);
                ph(f2, F2);
                break a;
              }
          }
          f2 = f2.return;
        } while (null !== f2);
      }
      Sk(c);
    } catch (na) {
      b = na;
      Y === c && null !== c && (Y = c = c.return);
      continue;
    }
    break;
  } while (1);
}
function Jk() {
  var a = mk.current;
  mk.current = Rh;
  return null === a ? Rh : a;
}
function tj() {
  if (0 === T || 3 === T || 2 === T) T = 4;
  null === Q || 0 === (rh & 268435455) && 0 === (qk & 268435455) || Ck(Q, Z);
}
function Ik(a, b) {
  var c = K;
  K |= 2;
  var d = Jk();
  if (Q !== a || Z !== b) uk = null, Kk(a, b);
  do
    try {
      Tk();
      break;
    } catch (e) {
      Mk(a, e);
    }
  while (1);
  $g();
  K = c;
  mk.current = d;
  if (null !== Y) throw Error(p(261));
  Q = null;
  Z = 0;
  return T;
}
function Tk() {
  for (; null !== Y; ) Uk(Y);
}
function Lk() {
  for (; null !== Y && !cc(); ) Uk(Y);
}
function Uk(a) {
  var b = Vk(a.alternate, a, fj);
  a.memoizedProps = a.pendingProps;
  null === b ? Sk(a) : Y = b;
  nk.current = null;
}
function Sk(a) {
  var b = a;
  do {
    var c = b.alternate;
    a = b.return;
    if (0 === (b.flags & 32768)) {
      if (c = Ej(c, b, fj), null !== c) {
        Y = c;
        return;
      }
    } else {
      c = Ij(c, b);
      if (null !== c) {
        c.flags &= 32767;
        Y = c;
        return;
      }
      if (null !== a) a.flags |= 32768, a.subtreeFlags = 0, a.deletions = null;
      else {
        T = 6;
        Y = null;
        return;
      }
    }
    b = b.sibling;
    if (null !== b) {
      Y = b;
      return;
    }
    Y = b = a;
  } while (null !== b);
  0 === T && (T = 5);
}
function Pk(a, b, c) {
  var d = C, e = ok.transition;
  try {
    ok.transition = null, C = 1, Wk(a, b, c, d);
  } finally {
    ok.transition = e, C = d;
  }
  return null;
}
function Wk(a, b, c, d) {
  do
    Hk();
  while (null !== wk);
  if (0 !== (K & 6)) throw Error(p(327));
  c = a.finishedWork;
  var e = a.finishedLanes;
  if (null === c) return null;
  a.finishedWork = null;
  a.finishedLanes = 0;
  if (c === a.current) throw Error(p(177));
  a.callbackNode = null;
  a.callbackPriority = 0;
  var f2 = c.lanes | c.childLanes;
  Bc(a, f2);
  a === Q && (Y = Q = null, Z = 0);
  0 === (c.subtreeFlags & 2064) && 0 === (c.flags & 2064) || vk || (vk = true, Fk(hc, function() {
    Hk();
    return null;
  }));
  f2 = 0 !== (c.flags & 15990);
  if (0 !== (c.subtreeFlags & 15990) || f2) {
    f2 = ok.transition;
    ok.transition = null;
    var g = C;
    C = 1;
    var h = K;
    K |= 4;
    nk.current = null;
    Oj(a, c);
    dk(c, a);
    Oe(Df);
    dd = !!Cf;
    Df = Cf = null;
    a.current = c;
    hk(c);
    dc();
    K = h;
    C = g;
    ok.transition = f2;
  } else a.current = c;
  vk && (vk = false, wk = a, xk = e);
  f2 = a.pendingLanes;
  0 === f2 && (Ri = null);
  mc(c.stateNode);
  Dk(a, B());
  if (null !== b) for (d = a.onRecoverableError, c = 0; c < b.length; c++) e = b[c], d(e.value, { componentStack: e.stack, digest: e.digest });
  if (Oi) throw Oi = false, a = Pi, Pi = null, a;
  0 !== (xk & 1) && 0 !== a.tag && Hk();
  f2 = a.pendingLanes;
  0 !== (f2 & 1) ? a === zk ? yk++ : (yk = 0, zk = a) : yk = 0;
  jg();
  return null;
}
function Hk() {
  if (null !== wk) {
    var a = Dc(xk), b = ok.transition, c = C;
    try {
      ok.transition = null;
      C = 16 > a ? 16 : a;
      if (null === wk) var d = false;
      else {
        a = wk;
        wk = null;
        xk = 0;
        if (0 !== (K & 6)) throw Error(p(331));
        var e = K;
        K |= 4;
        for (V = a.current; null !== V; ) {
          var f2 = V, g = f2.child;
          if (0 !== (V.flags & 16)) {
            var h = f2.deletions;
            if (null !== h) {
              for (var k2 = 0; k2 < h.length; k2++) {
                var l2 = h[k2];
                for (V = l2; null !== V; ) {
                  var m2 = V;
                  switch (m2.tag) {
                    case 0:
                    case 11:
                    case 15:
                      Pj(8, m2, f2);
                  }
                  var q2 = m2.child;
                  if (null !== q2) q2.return = m2, V = q2;
                  else for (; null !== V; ) {
                    m2 = V;
                    var r2 = m2.sibling, y2 = m2.return;
                    Sj(m2);
                    if (m2 === l2) {
                      V = null;
                      break;
                    }
                    if (null !== r2) {
                      r2.return = y2;
                      V = r2;
                      break;
                    }
                    V = y2;
                  }
                }
              }
              var n2 = f2.alternate;
              if (null !== n2) {
                var t2 = n2.child;
                if (null !== t2) {
                  n2.child = null;
                  do {
                    var J2 = t2.sibling;
                    t2.sibling = null;
                    t2 = J2;
                  } while (null !== t2);
                }
              }
              V = f2;
            }
          }
          if (0 !== (f2.subtreeFlags & 2064) && null !== g) g.return = f2, V = g;
          else b: for (; null !== V; ) {
            f2 = V;
            if (0 !== (f2.flags & 2048)) switch (f2.tag) {
              case 0:
              case 11:
              case 15:
                Pj(9, f2, f2.return);
            }
            var x2 = f2.sibling;
            if (null !== x2) {
              x2.return = f2.return;
              V = x2;
              break b;
            }
            V = f2.return;
          }
        }
        var w2 = a.current;
        for (V = w2; null !== V; ) {
          g = V;
          var u2 = g.child;
          if (0 !== (g.subtreeFlags & 2064) && null !== u2) u2.return = g, V = u2;
          else b: for (g = w2; null !== V; ) {
            h = V;
            if (0 !== (h.flags & 2048)) try {
              switch (h.tag) {
                case 0:
                case 11:
                case 15:
                  Qj(9, h);
              }
            } catch (na) {
              W(h, h.return, na);
            }
            if (h === g) {
              V = null;
              break b;
            }
            var F2 = h.sibling;
            if (null !== F2) {
              F2.return = h.return;
              V = F2;
              break b;
            }
            V = h.return;
          }
        }
        K = e;
        jg();
        if (lc && "function" === typeof lc.onPostCommitFiberRoot) try {
          lc.onPostCommitFiberRoot(kc, a);
        } catch (na) {
        }
        d = true;
      }
      return d;
    } finally {
      C = c, ok.transition = b;
    }
  }
  return false;
}
function Xk(a, b, c) {
  b = Ji(c, b);
  b = Ni(a, b, 1);
  a = nh(a, b, 1);
  b = R();
  null !== a && (Ac(a, 1, b), Dk(a, b));
}
function W(a, b, c) {
  if (3 === a.tag) Xk(a, a, c);
  else for (; null !== b; ) {
    if (3 === b.tag) {
      Xk(b, a, c);
      break;
    } else if (1 === b.tag) {
      var d = b.stateNode;
      if ("function" === typeof b.type.getDerivedStateFromError || "function" === typeof d.componentDidCatch && (null === Ri || !Ri.has(d))) {
        a = Ji(c, a);
        a = Qi(b, a, 1);
        b = nh(b, a, 1);
        a = R();
        null !== b && (Ac(b, 1, a), Dk(b, a));
        break;
      }
    }
    b = b.return;
  }
}
function Ti(a, b, c) {
  var d = a.pingCache;
  null !== d && d.delete(b);
  b = R();
  a.pingedLanes |= a.suspendedLanes & c;
  Q === a && (Z & c) === c && (4 === T || 3 === T && (Z & 130023424) === Z && 500 > B() - fk ? Kk(a, 0) : rk |= c);
  Dk(a, b);
}
function Yk(a, b) {
  0 === b && (0 === (a.mode & 1) ? b = 1 : (b = sc, sc <<= 1, 0 === (sc & 130023424) && (sc = 4194304)));
  var c = R();
  a = ih(a, b);
  null !== a && (Ac(a, b, c), Dk(a, c));
}
function uj(a) {
  var b = a.memoizedState, c = 0;
  null !== b && (c = b.retryLane);
  Yk(a, c);
}
function bk(a, b) {
  var c = 0;
  switch (a.tag) {
    case 13:
      var d = a.stateNode;
      var e = a.memoizedState;
      null !== e && (c = e.retryLane);
      break;
    case 19:
      d = a.stateNode;
      break;
    default:
      throw Error(p(314));
  }
  null !== d && d.delete(b);
  Yk(a, c);
}
var Vk;
Vk = function(a, b, c) {
  if (null !== a) if (a.memoizedProps !== b.pendingProps || Wf.current) dh = true;
  else {
    if (0 === (a.lanes & c) && 0 === (b.flags & 128)) return dh = false, yj(a, b, c);
    dh = 0 !== (a.flags & 131072) ? true : false;
  }
  else dh = false, I && 0 !== (b.flags & 1048576) && ug(b, ng, b.index);
  b.lanes = 0;
  switch (b.tag) {
    case 2:
      var d = b.type;
      ij(a, b);
      a = b.pendingProps;
      var e = Yf(b, H.current);
      ch(b, c);
      e = Nh(null, b, d, a, e, c);
      var f2 = Sh();
      b.flags |= 1;
      "object" === typeof e && null !== e && "function" === typeof e.render && void 0 === e.$$typeof ? (b.tag = 1, b.memoizedState = null, b.updateQueue = null, Zf(d) ? (f2 = true, cg(b)) : f2 = false, b.memoizedState = null !== e.state && void 0 !== e.state ? e.state : null, kh(b), e.updater = Ei, b.stateNode = e, e._reactInternals = b, Ii(b, d, a, c), b = jj(null, b, d, true, f2, c)) : (b.tag = 0, I && f2 && vg(b), Xi(null, b, e, c), b = b.child);
      return b;
    case 16:
      d = b.elementType;
      a: {
        ij(a, b);
        a = b.pendingProps;
        e = d._init;
        d = e(d._payload);
        b.type = d;
        e = b.tag = Zk(d);
        a = Ci(d, a);
        switch (e) {
          case 0:
            b = cj(null, b, d, a, c);
            break a;
          case 1:
            b = hj(null, b, d, a, c);
            break a;
          case 11:
            b = Yi(null, b, d, a, c);
            break a;
          case 14:
            b = $i(null, b, d, Ci(d.type, a), c);
            break a;
        }
        throw Error(p(
          306,
          d,
          ""
        ));
      }
      return b;
    case 0:
      return d = b.type, e = b.pendingProps, e = b.elementType === d ? e : Ci(d, e), cj(a, b, d, e, c);
    case 1:
      return d = b.type, e = b.pendingProps, e = b.elementType === d ? e : Ci(d, e), hj(a, b, d, e, c);
    case 3:
      a: {
        kj(b);
        if (null === a) throw Error(p(387));
        d = b.pendingProps;
        f2 = b.memoizedState;
        e = f2.element;
        lh(a, b);
        qh(b, d, null, c);
        var g = b.memoizedState;
        d = g.element;
        if (f2.isDehydrated) if (f2 = { element: d, isDehydrated: false, cache: g.cache, pendingSuspenseBoundaries: g.pendingSuspenseBoundaries, transitions: g.transitions }, b.updateQueue.baseState = f2, b.memoizedState = f2, b.flags & 256) {
          e = Ji(Error(p(423)), b);
          b = lj(a, b, d, c, e);
          break a;
        } else if (d !== e) {
          e = Ji(Error(p(424)), b);
          b = lj(a, b, d, c, e);
          break a;
        } else for (yg = Lf(b.stateNode.containerInfo.firstChild), xg = b, I = true, zg = null, c = Vg(b, null, d, c), b.child = c; c; ) c.flags = c.flags & -3 | 4096, c = c.sibling;
        else {
          Ig();
          if (d === e) {
            b = Zi(a, b, c);
            break a;
          }
          Xi(a, b, d, c);
        }
        b = b.child;
      }
      return b;
    case 5:
      return Ah(b), null === a && Eg(b), d = b.type, e = b.pendingProps, f2 = null !== a ? a.memoizedProps : null, g = e.children, Ef(d, e) ? g = null : null !== f2 && Ef(d, f2) && (b.flags |= 32), gj(a, b), Xi(a, b, g, c), b.child;
    case 6:
      return null === a && Eg(b), null;
    case 13:
      return oj(a, b, c);
    case 4:
      return yh(b, b.stateNode.containerInfo), d = b.pendingProps, null === a ? b.child = Ug(b, null, d, c) : Xi(a, b, d, c), b.child;
    case 11:
      return d = b.type, e = b.pendingProps, e = b.elementType === d ? e : Ci(d, e), Yi(a, b, d, e, c);
    case 7:
      return Xi(a, b, b.pendingProps, c), b.child;
    case 8:
      return Xi(a, b, b.pendingProps.children, c), b.child;
    case 12:
      return Xi(a, b, b.pendingProps.children, c), b.child;
    case 10:
      a: {
        d = b.type._context;
        e = b.pendingProps;
        f2 = b.memoizedProps;
        g = e.value;
        G(Wg, d._currentValue);
        d._currentValue = g;
        if (null !== f2) if (He(f2.value, g)) {
          if (f2.children === e.children && !Wf.current) {
            b = Zi(a, b, c);
            break a;
          }
        } else for (f2 = b.child, null !== f2 && (f2.return = b); null !== f2; ) {
          var h = f2.dependencies;
          if (null !== h) {
            g = f2.child;
            for (var k2 = h.firstContext; null !== k2; ) {
              if (k2.context === d) {
                if (1 === f2.tag) {
                  k2 = mh(-1, c & -c);
                  k2.tag = 2;
                  var l2 = f2.updateQueue;
                  if (null !== l2) {
                    l2 = l2.shared;
                    var m2 = l2.pending;
                    null === m2 ? k2.next = k2 : (k2.next = m2.next, m2.next = k2);
                    l2.pending = k2;
                  }
                }
                f2.lanes |= c;
                k2 = f2.alternate;
                null !== k2 && (k2.lanes |= c);
                bh(
                  f2.return,
                  c,
                  b
                );
                h.lanes |= c;
                break;
              }
              k2 = k2.next;
            }
          } else if (10 === f2.tag) g = f2.type === b.type ? null : f2.child;
          else if (18 === f2.tag) {
            g = f2.return;
            if (null === g) throw Error(p(341));
            g.lanes |= c;
            h = g.alternate;
            null !== h && (h.lanes |= c);
            bh(g, c, b);
            g = f2.sibling;
          } else g = f2.child;
          if (null !== g) g.return = f2;
          else for (g = f2; null !== g; ) {
            if (g === b) {
              g = null;
              break;
            }
            f2 = g.sibling;
            if (null !== f2) {
              f2.return = g.return;
              g = f2;
              break;
            }
            g = g.return;
          }
          f2 = g;
        }
        Xi(a, b, e.children, c);
        b = b.child;
      }
      return b;
    case 9:
      return e = b.type, d = b.pendingProps.children, ch(b, c), e = eh(e), d = d(e), b.flags |= 1, Xi(a, b, d, c), b.child;
    case 14:
      return d = b.type, e = Ci(d, b.pendingProps), e = Ci(d.type, e), $i(a, b, d, e, c);
    case 15:
      return bj(a, b, b.type, b.pendingProps, c);
    case 17:
      return d = b.type, e = b.pendingProps, e = b.elementType === d ? e : Ci(d, e), ij(a, b), b.tag = 1, Zf(d) ? (a = true, cg(b)) : a = false, ch(b, c), Gi(b, d, e), Ii(b, d, e, c), jj(null, b, d, true, a, c);
    case 19:
      return xj(a, b, c);
    case 22:
      return dj(a, b, c);
  }
  throw Error(p(156, b.tag));
};
function Fk(a, b) {
  return ac(a, b);
}
function $k(a, b, c, d) {
  this.tag = a;
  this.key = c;
  this.sibling = this.child = this.return = this.stateNode = this.type = this.elementType = null;
  this.index = 0;
  this.ref = null;
  this.pendingProps = b;
  this.dependencies = this.memoizedState = this.updateQueue = this.memoizedProps = null;
  this.mode = d;
  this.subtreeFlags = this.flags = 0;
  this.deletions = null;
  this.childLanes = this.lanes = 0;
  this.alternate = null;
}
function Bg(a, b, c, d) {
  return new $k(a, b, c, d);
}
function aj(a) {
  a = a.prototype;
  return !(!a || !a.isReactComponent);
}
function Zk(a) {
  if ("function" === typeof a) return aj(a) ? 1 : 0;
  if (void 0 !== a && null !== a) {
    a = a.$$typeof;
    if (a === Da) return 11;
    if (a === Ga) return 14;
  }
  return 2;
}
function Pg(a, b) {
  var c = a.alternate;
  null === c ? (c = Bg(a.tag, b, a.key, a.mode), c.elementType = a.elementType, c.type = a.type, c.stateNode = a.stateNode, c.alternate = a, a.alternate = c) : (c.pendingProps = b, c.type = a.type, c.flags = 0, c.subtreeFlags = 0, c.deletions = null);
  c.flags = a.flags & 14680064;
  c.childLanes = a.childLanes;
  c.lanes = a.lanes;
  c.child = a.child;
  c.memoizedProps = a.memoizedProps;
  c.memoizedState = a.memoizedState;
  c.updateQueue = a.updateQueue;
  b = a.dependencies;
  c.dependencies = null === b ? null : { lanes: b.lanes, firstContext: b.firstContext };
  c.sibling = a.sibling;
  c.index = a.index;
  c.ref = a.ref;
  return c;
}
function Rg(a, b, c, d, e, f2) {
  var g = 2;
  d = a;
  if ("function" === typeof a) aj(a) && (g = 1);
  else if ("string" === typeof a) g = 5;
  else a: switch (a) {
    case ya:
      return Tg(c.children, e, f2, b);
    case za:
      g = 8;
      e |= 8;
      break;
    case Aa:
      return a = Bg(12, c, b, e | 2), a.elementType = Aa, a.lanes = f2, a;
    case Ea:
      return a = Bg(13, c, b, e), a.elementType = Ea, a.lanes = f2, a;
    case Fa:
      return a = Bg(19, c, b, e), a.elementType = Fa, a.lanes = f2, a;
    case Ia:
      return pj(c, e, f2, b);
    default:
      if ("object" === typeof a && null !== a) switch (a.$$typeof) {
        case Ba:
          g = 10;
          break a;
        case Ca:
          g = 9;
          break a;
        case Da:
          g = 11;
          break a;
        case Ga:
          g = 14;
          break a;
        case Ha:
          g = 16;
          d = null;
          break a;
      }
      throw Error(p(130, null == a ? a : typeof a, ""));
  }
  b = Bg(g, c, b, e);
  b.elementType = a;
  b.type = d;
  b.lanes = f2;
  return b;
}
function Tg(a, b, c, d) {
  a = Bg(7, a, d, b);
  a.lanes = c;
  return a;
}
function pj(a, b, c, d) {
  a = Bg(22, a, d, b);
  a.elementType = Ia;
  a.lanes = c;
  a.stateNode = { isHidden: false };
  return a;
}
function Qg(a, b, c) {
  a = Bg(6, a, null, b);
  a.lanes = c;
  return a;
}
function Sg(a, b, c) {
  b = Bg(4, null !== a.children ? a.children : [], a.key, b);
  b.lanes = c;
  b.stateNode = { containerInfo: a.containerInfo, pendingChildren: null, implementation: a.implementation };
  return b;
}
function al(a, b, c, d, e) {
  this.tag = b;
  this.containerInfo = a;
  this.finishedWork = this.pingCache = this.current = this.pendingChildren = null;
  this.timeoutHandle = -1;
  this.callbackNode = this.pendingContext = this.context = null;
  this.callbackPriority = 0;
  this.eventTimes = zc(0);
  this.expirationTimes = zc(-1);
  this.entangledLanes = this.finishedLanes = this.mutableReadLanes = this.expiredLanes = this.pingedLanes = this.suspendedLanes = this.pendingLanes = 0;
  this.entanglements = zc(0);
  this.identifierPrefix = d;
  this.onRecoverableError = e;
  this.mutableSourceEagerHydrationData = null;
}
function bl(a, b, c, d, e, f2, g, h, k2) {
  a = new al(a, b, c, h, k2);
  1 === b ? (b = 1, true === f2 && (b |= 8)) : b = 0;
  f2 = Bg(3, null, null, b);
  a.current = f2;
  f2.stateNode = a;
  f2.memoizedState = { element: d, isDehydrated: c, cache: null, transitions: null, pendingSuspenseBoundaries: null };
  kh(f2);
  return a;
}
function cl(a, b, c) {
  var d = 3 < arguments.length && void 0 !== arguments[3] ? arguments[3] : null;
  return { $$typeof: wa, key: null == d ? null : "" + d, children: a, containerInfo: b, implementation: c };
}
function dl(a) {
  if (!a) return Vf;
  a = a._reactInternals;
  a: {
    if (Vb(a) !== a || 1 !== a.tag) throw Error(p(170));
    var b = a;
    do {
      switch (b.tag) {
        case 3:
          b = b.stateNode.context;
          break a;
        case 1:
          if (Zf(b.type)) {
            b = b.stateNode.__reactInternalMemoizedMergedChildContext;
            break a;
          }
      }
      b = b.return;
    } while (null !== b);
    throw Error(p(171));
  }
  if (1 === a.tag) {
    var c = a.type;
    if (Zf(c)) return bg(a, c, b);
  }
  return b;
}
function el(a, b, c, d, e, f2, g, h, k2) {
  a = bl(c, d, true, a, e, f2, g, h, k2);
  a.context = dl(null);
  c = a.current;
  d = R();
  e = yi(c);
  f2 = mh(d, e);
  f2.callback = void 0 !== b && null !== b ? b : null;
  nh(c, f2, e);
  a.current.lanes = e;
  Ac(a, e, d);
  Dk(a, d);
  return a;
}
function fl(a, b, c, d) {
  var e = b.current, f2 = R(), g = yi(e);
  c = dl(c);
  null === b.context ? b.context = c : b.pendingContext = c;
  b = mh(f2, g);
  b.payload = { element: a };
  d = void 0 === d ? null : d;
  null !== d && (b.callback = d);
  a = nh(e, b, g);
  null !== a && (gi(a, e, g, f2), oh(a, e, g));
  return g;
}
function gl(a) {
  a = a.current;
  if (!a.child) return null;
  switch (a.child.tag) {
    case 5:
      return a.child.stateNode;
    default:
      return a.child.stateNode;
  }
}
function hl(a, b) {
  a = a.memoizedState;
  if (null !== a && null !== a.dehydrated) {
    var c = a.retryLane;
    a.retryLane = 0 !== c && c < b ? c : b;
  }
}
function il(a, b) {
  hl(a, b);
  (a = a.alternate) && hl(a, b);
}
function jl() {
  return null;
}
var kl = "function" === typeof reportError ? reportError : function(a) {
  console.error(a);
};
function ll(a) {
  this._internalRoot = a;
}
ml.prototype.render = ll.prototype.render = function(a) {
  var b = this._internalRoot;
  if (null === b) throw Error(p(409));
  fl(a, b, null, null);
};
ml.prototype.unmount = ll.prototype.unmount = function() {
  var a = this._internalRoot;
  if (null !== a) {
    this._internalRoot = null;
    var b = a.containerInfo;
    Rk(function() {
      fl(null, a, null, null);
    });
    b[uf] = null;
  }
};
function ml(a) {
  this._internalRoot = a;
}
ml.prototype.unstable_scheduleHydration = function(a) {
  if (a) {
    var b = Hc();
    a = { blockedOn: null, target: a, priority: b };
    for (var c = 0; c < Qc.length && 0 !== b && b < Qc[c].priority; c++) ;
    Qc.splice(c, 0, a);
    0 === c && Vc(a);
  }
};
function nl(a) {
  return !(!a || 1 !== a.nodeType && 9 !== a.nodeType && 11 !== a.nodeType);
}
function ol(a) {
  return !(!a || 1 !== a.nodeType && 9 !== a.nodeType && 11 !== a.nodeType && (8 !== a.nodeType || " react-mount-point-unstable " !== a.nodeValue));
}
function pl() {
}
function ql(a, b, c, d, e) {
  if (e) {
    if ("function" === typeof d) {
      var f2 = d;
      d = function() {
        var a2 = gl(g);
        f2.call(a2);
      };
    }
    var g = el(b, d, a, 0, null, false, false, "", pl);
    a._reactRootContainer = g;
    a[uf] = g.current;
    sf(8 === a.nodeType ? a.parentNode : a);
    Rk();
    return g;
  }
  for (; e = a.lastChild; ) a.removeChild(e);
  if ("function" === typeof d) {
    var h = d;
    d = function() {
      var a2 = gl(k2);
      h.call(a2);
    };
  }
  var k2 = bl(a, 0, false, null, null, false, false, "", pl);
  a._reactRootContainer = k2;
  a[uf] = k2.current;
  sf(8 === a.nodeType ? a.parentNode : a);
  Rk(function() {
    fl(b, k2, c, d);
  });
  return k2;
}
function rl(a, b, c, d, e) {
  var f2 = c._reactRootContainer;
  if (f2) {
    var g = f2;
    if ("function" === typeof e) {
      var h = e;
      e = function() {
        var a2 = gl(g);
        h.call(a2);
      };
    }
    fl(b, g, a, e);
  } else g = ql(c, b, a, e, d);
  return gl(g);
}
Ec = function(a) {
  switch (a.tag) {
    case 3:
      var b = a.stateNode;
      if (b.current.memoizedState.isDehydrated) {
        var c = tc(b.pendingLanes);
        0 !== c && (Cc(b, c | 1), Dk(b, B()), 0 === (K & 6) && (Gj = B() + 500, jg()));
      }
      break;
    case 13:
      Rk(function() {
        var b2 = ih(a, 1);
        if (null !== b2) {
          var c2 = R();
          gi(b2, a, 1, c2);
        }
      }), il(a, 1);
  }
};
Fc = function(a) {
  if (13 === a.tag) {
    var b = ih(a, 134217728);
    if (null !== b) {
      var c = R();
      gi(b, a, 134217728, c);
    }
    il(a, 134217728);
  }
};
Gc = function(a) {
  if (13 === a.tag) {
    var b = yi(a), c = ih(a, b);
    if (null !== c) {
      var d = R();
      gi(c, a, b, d);
    }
    il(a, b);
  }
};
Hc = function() {
  return C;
};
Ic = function(a, b) {
  var c = C;
  try {
    return C = a, b();
  } finally {
    C = c;
  }
};
yb = function(a, b, c) {
  switch (b) {
    case "input":
      bb(a, c);
      b = c.name;
      if ("radio" === c.type && null != b) {
        for (c = a; c.parentNode; ) c = c.parentNode;
        c = c.querySelectorAll("input[name=" + JSON.stringify("" + b) + '][type="radio"]');
        for (b = 0; b < c.length; b++) {
          var d = c[b];
          if (d !== a && d.form === a.form) {
            var e = Db(d);
            if (!e) throw Error(p(90));
            Wa(d);
            bb(d, e);
          }
        }
      }
      break;
    case "textarea":
      ib(a, c);
      break;
    case "select":
      b = c.value, null != b && fb(a, !!c.multiple, b, false);
  }
};
Gb = Qk;
Hb = Rk;
var sl = { usingClientEntryPoint: false, Events: [Cb, ue, Db, Eb, Fb, Qk] }, tl = { findFiberByHostInstance: Wc, bundleType: 0, version: "18.3.1", rendererPackageName: "react-dom" };
var ul = { bundleType: tl.bundleType, version: tl.version, rendererPackageName: tl.rendererPackageName, rendererConfig: tl.rendererConfig, overrideHookState: null, overrideHookStateDeletePath: null, overrideHookStateRenamePath: null, overrideProps: null, overridePropsDeletePath: null, overridePropsRenamePath: null, setErrorHandler: null, setSuspenseHandler: null, scheduleUpdate: null, currentDispatcherRef: ua.ReactCurrentDispatcher, findHostInstanceByFiber: function(a) {
  a = Zb(a);
  return null === a ? null : a.stateNode;
}, findFiberByHostInstance: tl.findFiberByHostInstance || jl, findHostInstancesForRefresh: null, scheduleRefresh: null, scheduleRoot: null, setRefreshHandler: null, getCurrentFiber: null, reconcilerVersion: "18.3.1-next-f1338f8080-20240426" };
if ("undefined" !== typeof __REACT_DEVTOOLS_GLOBAL_HOOK__) {
  var vl = __REACT_DEVTOOLS_GLOBAL_HOOK__;
  if (!vl.isDisabled && vl.supportsFiber) try {
    kc = vl.inject(ul), lc = vl;
  } catch (a) {
  }
}
reactDom_production_min.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED = sl;
reactDom_production_min.createPortal = function(a, b) {
  var c = 2 < arguments.length && void 0 !== arguments[2] ? arguments[2] : null;
  if (!nl(b)) throw Error(p(200));
  return cl(a, b, null, c);
};
reactDom_production_min.createRoot = function(a, b) {
  if (!nl(a)) throw Error(p(299));
  var c = false, d = "", e = kl;
  null !== b && void 0 !== b && (true === b.unstable_strictMode && (c = true), void 0 !== b.identifierPrefix && (d = b.identifierPrefix), void 0 !== b.onRecoverableError && (e = b.onRecoverableError));
  b = bl(a, 1, false, null, null, c, false, d, e);
  a[uf] = b.current;
  sf(8 === a.nodeType ? a.parentNode : a);
  return new ll(b);
};
reactDom_production_min.findDOMNode = function(a) {
  if (null == a) return null;
  if (1 === a.nodeType) return a;
  var b = a._reactInternals;
  if (void 0 === b) {
    if ("function" === typeof a.render) throw Error(p(188));
    a = Object.keys(a).join(",");
    throw Error(p(268, a));
  }
  a = Zb(b);
  a = null === a ? null : a.stateNode;
  return a;
};
reactDom_production_min.flushSync = function(a) {
  return Rk(a);
};
reactDom_production_min.hydrate = function(a, b, c) {
  if (!ol(b)) throw Error(p(200));
  return rl(null, a, b, true, c);
};
reactDom_production_min.hydrateRoot = function(a, b, c) {
  if (!nl(a)) throw Error(p(405));
  var d = null != c && c.hydratedSources || null, e = false, f2 = "", g = kl;
  null !== c && void 0 !== c && (true === c.unstable_strictMode && (e = true), void 0 !== c.identifierPrefix && (f2 = c.identifierPrefix), void 0 !== c.onRecoverableError && (g = c.onRecoverableError));
  b = el(b, null, a, 1, null != c ? c : null, e, false, f2, g);
  a[uf] = b.current;
  sf(a);
  if (d) for (a = 0; a < d.length; a++) c = d[a], e = c._getVersion, e = e(c._source), null == b.mutableSourceEagerHydrationData ? b.mutableSourceEagerHydrationData = [c, e] : b.mutableSourceEagerHydrationData.push(
    c,
    e
  );
  return new ml(b);
};
reactDom_production_min.render = function(a, b, c) {
  if (!ol(b)) throw Error(p(200));
  return rl(null, a, b, false, c);
};
reactDom_production_min.unmountComponentAtNode = function(a) {
  if (!ol(a)) throw Error(p(40));
  return a._reactRootContainer ? (Rk(function() {
    rl(null, null, a, false, function() {
      a._reactRootContainer = null;
      a[uf] = null;
    });
  }), true) : false;
};
reactDom_production_min.unstable_batchedUpdates = Qk;
reactDom_production_min.unstable_renderSubtreeIntoContainer = function(a, b, c, d) {
  if (!ol(c)) throw Error(p(200));
  if (null == a || void 0 === a._reactInternals) throw Error(p(38));
  return rl(a, b, c, false, d);
};
reactDom_production_min.version = "18.3.1-next-f1338f8080-20240426";
function checkDCE() {
  if (typeof __REACT_DEVTOOLS_GLOBAL_HOOK__ === "undefined" || typeof __REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE !== "function") {
    return;
  }
  try {
    __REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE(checkDCE);
  } catch (err) {
    console.error(err);
  }
}
{
  checkDCE();
  reactDom.exports = reactDom_production_min;
}
var reactDomExports = reactDom.exports;
var m = reactDomExports;
{
  client.createRoot = m.createRoot;
  client.hydrateRoot = m.hydrateRoot;
}
const createStoreImpl = (createState) => {
  let state;
  const listeners = /* @__PURE__ */ new Set();
  const setState = (partial, replace) => {
    const nextState = typeof partial === "function" ? partial(state) : partial;
    if (!Object.is(nextState, state)) {
      const previousState = state;
      state = (replace != null ? replace : typeof nextState !== "object" || nextState === null) ? nextState : Object.assign({}, state, nextState);
      listeners.forEach((listener) => listener(state, previousState));
    }
  };
  const getState = () => state;
  const getInitialState = () => initialState;
  const subscribe = (listener) => {
    listeners.add(listener);
    return () => listeners.delete(listener);
  };
  const api = { setState, getState, getInitialState, subscribe };
  const initialState = state = createState(setState, getState, api);
  return api;
};
const createStore = (createState) => createState ? createStoreImpl(createState) : createStoreImpl;
const identity = (arg) => arg;
function useStore(api, selector = identity) {
  const slice = React.useSyncExternalStore(
    api.subscribe,
    React.useCallback(() => selector(api.getState()), [api, selector]),
    React.useCallback(() => selector(api.getInitialState()), [api, selector])
  );
  React.useDebugValue(slice);
  return slice;
}
const createImpl = (createState) => {
  const api = createStore(createState);
  const useBoundStore = (selector) => useStore(api, selector);
  Object.assign(useBoundStore, api);
  return useBoundStore;
};
const create = (createState) => createState ? createImpl(createState) : createImpl;
const useChatStore = create(
  (set, get) => ({
    messages: [],
    isLoading: false,
    port: null,
    sidecarError: null,
    brokerStatus: { connected: false, broker: null },
    brokerStatuses: {},
    // full /api/status response
    streamCancel: null,
    // () => void — closes the active EventSource
    setPort: (port) => set({ port, sidecarError: null }),
    setSidecarError: (msg) => set({ sidecarError: msg }),
    setBrokerStatus: (status) => set({ brokerStatus: status }),
    setBrokerStatuses: (statuses) => {
      const connected = Object.values(statuses).some((b) => b.authenticated);
      const broker = Object.entries(statuses).find(([, b]) => b.authenticated)?.[0] ?? null;
      const name = broker ? { zerodha: "Zerodha", groww: "Groww", angel_one: "Angel One", upstox: "Upstox", fyers: "Fyers" }[broker] ?? broker : null;
      set({ brokerStatuses: statuses, brokerStatus: { connected, broker: name } });
    },
    addUserMessage: (text) => set((s) => ({
      messages: [...s.messages, {
        id: Date.now(),
        role: "user",
        text
      }],
      isLoading: true
    })),
    addResponse: (card) => set((s) => ({
      messages: [...s.messages, { id: Date.now() + 1, role: "assistant", ...card }],
      isLoading: false
    })),
    addError: (text) => set((s) => ({
      messages: [...s.messages, { id: Date.now() + 1, role: "error", text }],
      isLoading: false
    })),
    setLoading: (v2) => set({ isLoading: v2 }),
    setStreamCancel: (fn) => set({ streamCancel: fn }),
    cancelStream: () => {
      const { streamCancel } = get();
      if (streamCancel) {
        streamCancel();
        set({ streamCancel: null, isLoading: false });
      }
    },
    // Streaming support — used by analyze SSE
    startStreamingMessage: (id2, symbol, exchange) => set((s) => ({
      messages: [...s.messages, {
        id: id2,
        role: "assistant",
        cardType: "streaming_analysis",
        data: { symbol, exchange, analysts: [], debate_steps: [], synthesis_text: null, phase: "analysts", report: null, trade_plans: null }
      }],
      isLoading: true
    })),
    updateStreamingMessage: (id2, updater) => set((s) => ({
      messages: s.messages.map((m2) => m2.id === id2 ? { ...m2, data: updater(m2.data) } : m2)
    })),
    finalizeStreamingMessage: (_id) => set({ isLoading: false }),
    // Draft message — lets cards pre-fill the input bar
    draft: "",
    setDraft: (text) => set({ draft: text }),
    // Context queued while a streaming analysis is running (#102)
    // Shown as a user bubble and auto-injected into the first follow-up
    pendingContext: "",
    setPendingContext: (text) => set({ pendingContext: text }),
    clearPendingContext: () => set({ pendingContext: "" })
  })
);
const IST_OFFSET_MS = 5.5 * 60 * 60 * 1e3;
function getISTTime() {
  const now = /* @__PURE__ */ new Date();
  const utcMs = now.getTime() + now.getTimezoneOffset() * 6e4;
  return new Date(utcMs + IST_OFFSET_MS);
}
function getMarketStatus() {
  const ist = getISTTime();
  const day = ist.getDay();
  const hhmm = ist.getHours() * 100 + ist.getMinutes();
  if (day === 0 || day === 6) return "closed";
  if (hhmm >= 900 && hhmm < 915) return "pre-open";
  if (hhmm >= 915 && hhmm < 1530) return "open";
  if (hhmm >= 1530 && hhmm < 1600) return "post-close";
  return "closed";
}
function useMarketClock() {
  const port = useChatStore((s) => s.port);
  const [status, setStatus] = reactExports.useState(getMarketStatus);
  const [nifty, setNifty] = reactExports.useState(null);
  const [banknifty, setBanknifty] = reactExports.useState(null);
  const pollRef = reactExports.useRef(null);
  reactExports.useEffect(() => {
    const t2 = setInterval(() => setStatus(getMarketStatus()), 6e4);
    return () => clearInterval(t2);
  }, []);
  async function fetchNifty() {
    if (!port) return;
    try {
      const res = await fetch(`http://127.0.0.1:${port}/skills/quote?symbol=NIFTY50&exchange=NSE`);
      if (!res.ok) return;
      const data = await res.json();
      const ltp = data?.data?.ltp ?? data?.ltp;
      if (ltp != null) {
        const formatted = Number(ltp).toLocaleString("en-IN", { maximumFractionDigits: 0 });
        setNifty(formatted);
        window.electronAPI?.updateTray({ label: `N ${formatted}` });
      }
    } catch (_) {
    }
  }
  reactExports.useEffect(() => {
    if (!port) return;
    if (pollRef.current) clearInterval(pollRef.current);
    fetchNifty();
    const interval = status === "open" || status === "pre-open" ? 6e4 : 3e5;
    pollRef.current = setInterval(fetchNifty, interval);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [port, status]);
  reactExports.useEffect(() => {
    if (status === "closed") {
      window.electronAPI?.updateTray({ label: null });
    }
  }, [status]);
  return { status, nifty, banknifty };
}
function useAPI() {
  const port = useChatStore((s) => s.port);
  const base = window.__INDIA_TRADE_WEB__ ? window.location.origin : port ? `http://127.0.0.1:${port}` : null;
  const fetchOpts = window.__INDIA_TRADE_WEB__ ? { credentials: "include" } : {};
  const call = async (endpoint, body = {}) => {
    if (!base) throw new Error("API not ready — sidecar is still starting");
    const res = await fetch(`${base}${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      ...fetchOpts
    });
    if (!res.ok) {
      if (res.status === 401 && window.__INDIA_TRADE_WEB__) {
        window.location.href = "/";
        return;
      }
      const err = await res.text();
      throw new Error(`API ${res.status}: ${err}`);
    }
    return res.json();
  };
  const get = async (endpoint) => {
    if (!base) throw new Error("API not ready");
    const res = await fetch(`${base}${endpoint}`, fetchOpts);
    if (!res.ok) {
      if (res.status === 401 && window.__INDIA_TRADE_WEB__) {
        window.location.href = "/";
        return;
      }
      throw new Error(`API ${res.status}`);
    }
    return res.json();
  };
  return { call, get, ready: !!base, base };
}
const BROKERS$1 = [
  {
    key: "fyers",
    name: "Fyers",
    color: "text-[#fed7aa]",
    loginPath: "/fyers/login",
    portalUrl: "https://myapi.fyers.in",
    portalLabel: "myapi.fyers.in",
    redirectUrl: "http://127.0.0.1:8765/fyers/callback",
    keys: [
      { env: "FYERS_APP_ID", label: "App ID", placeholder: "XXXX-100", secret: false },
      { env: "FYERS_SECRET_KEY", label: "Secret Key", placeholder: "Secret key", secret: true }
    ]
  },
  {
    key: "zerodha",
    name: "Zerodha",
    color: "text-[#387ed1]",
    loginPath: "/zerodha/login",
    portalUrl: "https://developers.kite.trade",
    portalLabel: "developers.kite.trade",
    redirectUrl: "http://localhost:8765/zerodha/callback",
    keys: [
      { env: "KITE_API_KEY", label: "API Key", placeholder: "API key", secret: false },
      { env: "KITE_API_SECRET", label: "API Secret", placeholder: "API secret", secret: true }
    ]
  },
  {
    key: "angel_one",
    name: "Angel One",
    color: "text-[#f6882a]",
    loginPath: "/angelone/login",
    keys: []
  },
  {
    key: "upstox",
    name: "Upstox",
    color: "text-[#c4b5fd]",
    loginPath: "/upstox/login",
    keys: []
  },
  {
    key: "groww",
    name: "Groww",
    color: "text-[#00c48c]",
    loginPath: "/groww/login",
    keys: []
  }
];
function BrokerPanel({ onClose }) {
  const port = useChatStore((s) => s.port);
  const brokerStatuses = useChatStore((s) => s.brokerStatuses);
  const setBrokerStatuses = useChatStore((s) => s.setBrokerStatuses);
  const [disconnecting, setDisconnecting] = reactExports.useState(null);
  const [expandedBroker, setExpandedBroker] = reactExports.useState(null);
  const [error, setError] = reactExports.useState(null);
  const [saving, setSaving] = reactExports.useState(false);
  const [successBroker, setSuccessBroker] = reactExports.useState(null);
  const base = `http://127.0.0.1:${port}`;
  const pollRef = { current: null };
  function openLoginAndPoll(broker) {
    window.electronAPI?.openExternal(`${base}${broker.loginPath}`);
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${base}/api/status`);
        const data = await res.json();
        setBrokerStatuses(data);
        if (data[broker.key]?.authenticated) {
          clearInterval(pollRef.current);
          pollRef.current = null;
          setExpandedBroker(null);
          setSuccessBroker(broker.name);
          setTimeout(() => onClose(), 1500);
        }
      } catch {
      }
    }, 2e3);
  }
  async function disconnect(brokerKey) {
    setDisconnecting(brokerKey);
    setError(null);
    try {
      const r2 = await fetch(`${base}/api/broker/${brokerKey}`, { method: "DELETE" });
      if (!r2.ok) {
        const body = await r2.json().catch(() => ({}));
        throw new Error(body.detail ?? `HTTP ${r2.status}`);
      }
      const res = await fetch(`${base}/api/status`);
      const data = await res.json();
      setBrokerStatuses(data);
    } catch (e) {
      setError(e.message);
    }
    setDisconnecting(null);
  }
  async function saveKeysAndLogin(broker) {
    setSaving(true);
    setError(null);
    try {
      const inputs = document.querySelectorAll(`[data-broker-panel="${broker.key}"]`);
      for (const input of inputs) {
        if (!input.value.trim()) {
          setError(`Please fill in all fields for ${broker.name}`);
          setSaving(false);
          return;
        }
        await fetch(`${base}/api/onboarding/credential`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ key: input.dataset.key, value: input.value.trim() })
        });
      }
      const res = await fetch(`${base}/api/status`);
      setBrokerStatuses(await res.json());
      openLoginAndPoll(broker);
    } catch (e) {
      setError(e.message);
    }
    setSaving(false);
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "fixed inset-0 z-50 flex items-center justify-center bg-black/60", onClick: onClose, children: /* @__PURE__ */ jsxRuntimeExports.jsxs(
    "div",
    {
      className: "w-[480px] max-h-[80vh] flex flex-col bg-panel border border-border rounded-xl shadow-2xl",
      onClick: (e) => e.stopPropagation(),
      children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between px-4 py-3 border-b border-border flex-shrink-0", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-text text-[13px] font-semibold font-ui", children: "Brokers" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "button",
            {
              onClick: onClose,
              className: "text-muted hover:text-text text-lg transition-colors leading-none cursor-pointer",
              children: "×"
            }
          )
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex-1 overflow-y-auto px-3 py-3 space-y-2", children: BROKERS$1.map((broker) => {
          const status = brokerStatuses[broker.key] ?? { configured: false, authenticated: false };
          const isExpanded = expandedBroker === broker.key;
          return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-elevated rounded-lg border border-border overflow-hidden", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between p-3", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `w-2 h-2 rounded-full flex-shrink-0 ${status.authenticated ? "bg-green shadow-[0_0_6px_rgba(82,224,122,0.4)]" : status.configured ? "bg-amber/50" : "bg-subtle"}` }),
                /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `text-[13px] font-semibold font-ui ${broker.color}`, children: broker.name })
              ] }),
              status.authenticated ? /* @__PURE__ */ jsxRuntimeExports.jsx(
                "button",
                {
                  onClick: () => disconnect(broker.key),
                  disabled: disconnecting === broker.key,
                  className: "text-[11px] font-ui px-2.5 py-1 rounded-md border border-red/30\n                               text-red hover:bg-red/10 transition-colors disabled:opacity-40 cursor-pointer",
                  children: disconnecting === broker.key ? "..." : "Disconnect"
                }
              ) : status.configured ? /* @__PURE__ */ jsxRuntimeExports.jsx(
                "button",
                {
                  onClick: () => openLoginAndPoll(broker),
                  className: "text-[11px] font-ui px-2.5 py-1 rounded-md border border-green/30\n                               text-green hover:bg-green/10 transition-colors cursor-pointer",
                  children: "Connect"
                }
              ) : broker.keys.length > 0 ? /* @__PURE__ */ jsxRuntimeExports.jsx(
                "button",
                {
                  onClick: () => setExpandedBroker(isExpanded ? null : broker.key),
                  className: `text-[11px] font-ui px-2.5 py-1 rounded-md border transition-colors cursor-pointer
                      ${isExpanded ? "border-amber/30 text-amber bg-amber/10" : "border-border text-muted hover:text-text"}`,
                  children: isExpanded ? "Hide" : "Set Up"
                }
              ) : /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-subtle text-[10px] font-ui", children: "Coming soon" })
            ] }),
            isExpanded && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "p-3 border-t border-border space-y-3", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsxs(
                "button",
                {
                  onClick: () => window.electronAPI?.openExternal(broker.portalUrl),
                  className: "w-full text-left text-amber text-[11px] font-ui hover:underline cursor-pointer",
                  children: [
                    "Create app at ",
                    broker.portalLabel,
                    " →"
                  ]
                }
              ),
              /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] font-ui mb-1", children: "Redirect URL (set this in your broker app):" }),
                /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-1", children: [
                  /* @__PURE__ */ jsxRuntimeExports.jsx("code", { className: "flex-1 bg-panel text-amber text-[10px] font-mono px-2 py-1.5 rounded border border-border truncate", children: broker.redirectUrl }),
                  /* @__PURE__ */ jsxRuntimeExports.jsx(
                    "button",
                    {
                      onClick: () => navigator.clipboard.writeText(broker.redirectUrl),
                      className: "text-muted hover:text-text text-[10px] px-1.5 py-1.5 border border-border rounded cursor-pointer",
                      children: "Copy"
                    }
                  )
                ] })
              ] }),
              broker.keys.map((key) => /* @__PURE__ */ jsxRuntimeExports.jsx(
                "input",
                {
                  "data-broker-panel": broker.key,
                  "data-key": key.env,
                  type: key.secret ? "password" : "text",
                  placeholder: key.label,
                  className: "w-full bg-panel border border-border rounded-lg px-3 py-2\n                                 text-text text-xs font-mono placeholder:text-subtle\n                                 focus:outline-none focus:border-amber"
                },
                key.env
              )),
              /* @__PURE__ */ jsxRuntimeExports.jsx(
                "button",
                {
                  onClick: () => saveKeysAndLogin(broker),
                  disabled: saving,
                  className: "w-full px-3 py-2 bg-green/10 text-green border border-green/30\n                               rounded-lg text-xs font-ui font-semibold hover:bg-green/20\n                               transition-all disabled:opacity-40 cursor-pointer",
                  children: saving ? "Saving..." : "Save & Connect"
                }
              )
            ] })
          ] }, broker.key);
        }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "px-4 py-3 border-t border-border flex-shrink-0 space-y-1.5", children: [
          successBroker && /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-green text-sm font-ui font-semibold text-center py-2", children: [
            successBroker,
            " connected successfully"
          ] }),
          error && /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-red text-[10px] font-ui", children: [
            "Error: ",
            error
          ] }),
          !successBroker && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-subtle text-[10px] font-ui leading-relaxed", children: "Login opens your browser. OAuth completes automatically." })
        ] })
      ]
    }
  ) });
}
const QUICK_COMMANDS = [
  { label: "Morning Brief", icon: "☀️", command: "morning-brief" },
  { label: "Holdings", icon: "📊", command: "holdings" },
  { label: "Positions", icon: "📈", command: "positions" },
  { label: "Orders", icon: "📋", command: "orders" },
  { label: "Funds", icon: "💰", command: "funds" },
  { label: "Alerts", icon: "🔔", command: "alerts" },
  { label: "FII/DII Flows", icon: "🌊", command: "flows" },
  { label: "Patterns", icon: "🔍", command: "patterns" },
  { label: "Scan", icon: "📡", command: "scan" },
  // ── Analysis ──────────────────────────────────────────────
  { label: "GEX", icon: "⚡", command: "gex NIFTY" },
  { label: "IV Smile", icon: "📉", command: "iv-smile NIFTY" },
  { label: "Risk Report", icon: "🛡", command: "risk-report" },
  { label: "Strategy", icon: "🎯", command: "strategy NIFTY bullish" },
  // ── Portfolio ─────────────────────────────────────────────
  { label: "Delta Hedge", icon: "⚖️", command: "delta-hedge" },
  { label: "What-If", icon: "🔮", command: "whatif" },
  { label: "Drift", icon: "📐", command: "drift" },
  { label: "Memory", icon: "🧠", command: "memory" }
];
function Sidebar() {
  const { addUserMessage, addResponse, addError, isLoading, brokerStatus, port } = useChatStore();
  const { call, ready } = useAPI();
  const [showBrokerPanel, setShowBrokerPanel] = reactExports.useState(false);
  async function runCommand(command) {
    if (!ready || isLoading) return;
    addUserMessage(command);
    try {
      const data = await routeCommand(call, command);
      addResponse(data);
    } catch (e) {
      addError(e.message);
    }
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "w-56 flex-shrink-0 bg-panel border-r border-border flex flex-col relative", children: [
    showBrokerPanel && /* @__PURE__ */ jsxRuntimeExports.jsx(BrokerPanel, { onClose: () => setShowBrokerPanel(false) }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs(
      "div",
      {
        className: "px-4 py-3 border-b border-border cursor-pointer hover:bg-elevated transition-colors group",
        onClick: () => setShowBrokerPanel(true),
        children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-widest mb-2 font-ui", children: "Broker" }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 min-w-0", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `w-2 h-2 rounded-full flex-shrink-0 transition-all ${brokerStatus.connected ? "bg-green shadow-[0_0_6px_rgba(82,224,122,0.4)]" : "bg-subtle"}` }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-text text-[12px] font-ui truncate", children: brokerStatus.connected ? brokerStatus.broker : port ? "Not connected" : "Starting…" })
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-subtle text-[10px] font-ui opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0 ml-1", children: brokerStatus.connected ? "manage" : "connect" })
          ] })
        ]
      }
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "px-3 py-3 flex-1", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-widest mb-2 px-1 font-ui", children: "Quick" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex flex-col gap-1", children: QUICK_COMMANDS.map((q2) => /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          onClick: () => runCommand(q2.command),
          disabled: !ready || isLoading,
          className: "flex items-center gap-2 px-2 py-1.5 rounded text-[12px] text-text\n                         hover:bg-elevated transition-colors disabled:opacity-40\n                         text-left font-ui",
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: q2.icon }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: q2.label })
          ]
        },
        q2.command
      )) })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "px-4 py-3 border-t border-border", children: /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-subtle text-[10px] font-ui", children: "India Trade v0.2" }) })
  ] });
}
async function routeCommand(call, command) {
  const unwrap = (res) => res.data ?? res;
  switch (command) {
    case "morning-brief":
      return { cardType: "morning_brief", data: unwrap(await call("/skills/morning_brief", {})) };
    case "holdings":
      return { cardType: "holdings", data: unwrap(await call("/skills/holdings", {})) };
    case "positions":
      return { cardType: "holdings", data: unwrap(await call("/skills/positions", {})) };
    case "flows": {
      const fd2 = unwrap(await call("/skills/flows", {}));
      return { cardType: "flows", data: fd2?.flow_analysis ?? fd2 };
    }
    case "orders":
      return { cardType: "orders", data: unwrap(await call("/skills/orders", {})) };
    case "funds":
      return { cardType: "funds", data: unwrap(await call("/skills/funds", {})) };
    case "alerts":
      return { cardType: "alerts", data: unwrap(await call("/skills/alerts/list", {})) };
    case "patterns":
      return { cardType: "patterns", data: unwrap(await call("/skills/patterns", {})) };
    case "scan":
      return { cardType: "scan", data: unwrap(await call("/skills/scan", { scan_type: "options", filters: {} })) };
    case "gex NIFTY":
      return { cardType: "gex", data: unwrap(await call("/skills/gex", { symbol: "NIFTY", expiry: null })) };
    case "iv-smile NIFTY":
      return { cardType: "iv_smile", data: unwrap(await call("/skills/iv_smile", { symbol: "NIFTY", expiry: null })) };
    case "risk-report":
      return { cardType: "risk_report", data: unwrap(await call("/skills/risk_report", {})) };
    case "strategy NIFTY bullish":
      return { cardType: "strategy", data: unwrap(await call("/skills/strategy", { symbol: "NIFTY", view: "BULLISH", dte: 30 })) };
    case "delta-hedge":
      return { cardType: "delta_hedge", data: unwrap(await call("/skills/delta_hedge", {})) };
    case "whatif":
      return { cardType: "whatif", data: unwrap(await call("/skills/whatif", { scenario: "market" })) };
    case "drift":
      return { cardType: "drift", data: unwrap(await call("/skills/drift", {})) };
    case "memory":
      return { cardType: "memory", data: unwrap(await call("/skills/memory", {})) };
    default:
      throw new Error(`Unknown command: ${command}`);
  }
}
function QuoteCard({ data }) {
  if (!data) return /* @__PURE__ */ jsxRuntimeExports.jsx(Card$1, { children: /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-sm", children: "No quote data." }) });
  const ltp = data.last_price ?? data.ltp ?? 0;
  const change = data.change ?? data.net_change ?? 0;
  const changePct = data.change_pct ?? data.pct_change ?? 0;
  const symbol = data.symbol ?? data.tradingsymbol ?? "—";
  const positive = change >= 0;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(Card$1, { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-start justify-between", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[11px] uppercase tracking-widest font-ui mb-1", children: "Quote" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-text text-xl font-semibold font-mono", children: symbol }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-xs font-ui mt-0.5", children: data.exchange ?? "NSE" })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "text-right", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-text text-2xl font-mono font-semibold", children: [
          "₹",
          fmt$5(ltp)
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: `text-sm font-mono mt-1 ${positive ? "text-green" : "text-red"}`, children: [
          positive ? "+" : "",
          Number(change).toFixed(2),
          " ",
          "(",
          positive ? "+" : "",
          Number(changePct).toFixed(2),
          "%)"
        ] })
      ] })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid grid-cols-4 gap-3 mt-4 pt-4 border-t border-border", children: [
      ["Open", `₹${fmt$5(data.open)}`],
      ["High", `₹${fmt$5(data.high)}`],
      ["Low", `₹${fmt$5(data.low)}`],
      ["Volume", vol(data.volume)]
    ].map(([label, val]) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-wider font-ui", children: label }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-text text-sm font-mono mt-0.5", children: val })
    ] }, label)) })
  ] });
}
const fmt$5 = (n2) => Number(n2 ?? 0).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const vol = (n2) => {
  const v2 = Number(n2 ?? 0);
  if (v2 >= 1e7) return `${(v2 / 1e7).toFixed(2)}Cr`;
  if (v2 >= 1e5) return `${(v2 / 1e5).toFixed(2)}L`;
  return v2.toLocaleString("en-IN");
};
function Card$1({ children }) {
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "bg-elevated border border-border rounded-xl p-4 max-w-md w-full", children });
}
function AnalysisCard({ data }) {
  const [showPlans, setShowPlans] = reactExports.useState(false);
  if (!data) return null;
  const { symbol, exchange, report, trade_plans } = data;
  const plans = trade_plans ? Object.entries(trade_plans).filter(([, v2]) => v2 != null) : [];
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-elevated border border-blue/30 rounded-xl p-4 max-w-2xl w-full space-y-4", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[11px] uppercase tracking-widest font-ui", children: "Analysis" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-text text-lg font-semibold font-mono mt-0.5", children: [
          symbol,
          " ",
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-muted text-sm font-ui", children: exchange })
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-blue text-xl", children: "🔬" })
    ] }),
    report && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "border-t border-border pt-3", children: /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-text text-sm font-ui leading-relaxed whitespace-pre-wrap", children: report }) }),
    plans.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "border-t border-border pt-3", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          onClick: () => setShowPlans((v2) => !v2),
          className: "text-amber text-xs font-ui hover:opacity-80 transition-opacity",
          children: [
            showPlans ? "▾ Hide" : "▸ Show",
            " trade plans (",
            plans.length,
            ")"
          ]
        }
      ),
      showPlans && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mt-3 space-y-3", children: plans.map(([name, plan]) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-panel rounded-lg p-3 border border-border", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-amber text-xs font-ui uppercase tracking-wider mb-2", children: name }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("pre", { className: "text-text text-xs font-mono whitespace-pre-wrap leading-relaxed", children: typeof plan === "string" ? plan : JSON.stringify(plan, null, 2) })
      ] }, name)) })
    ] })
  ] });
}
const ANALYSTS = [
  "Technical",
  "Fundamental",
  "Options",
  "News & Macro",
  "Sentiment",
  "Sector Rotation",
  "Risk Manager"
];
const DISPLAY_NAMES = {
  "Technical": "Technical",
  "Fundamental": "Fundamental",
  "Options": "Options",
  "News & Macro": "News / Macro",
  "Sentiment": "Sentiment",
  "Sector Rotation": "Sector",
  "Risk Manager": "Risk"
};
const VERDICT_COLOR = {
  BUY: "text-green border-green/40 bg-green/5",
  SELL: "text-red border-red/40 bg-red/5",
  HOLD: "text-amber border-amber/40 bg-amber/5",
  BULLISH: "text-green border-green/40 bg-green/5",
  BEARISH: "text-red border-red/40 bg-red/5",
  NEUTRAL: "text-amber border-amber/40 bg-amber/5",
  UNKNOWN: "text-muted border-border/40"
};
const STEP_META = {
  bull_r1: { label: "Bull Researcher", color: "text-green", icon: "▲" },
  bear_r1: { label: "Bear Researcher", color: "text-red", icon: "▼" },
  bull_r2: { label: "Bull Rebuttal", color: "text-green", icon: "▲" },
  bear_r2: { label: "Bear Rebuttal", color: "text-red", icon: "▼" },
  facilitator: { label: "Facilitator", color: "text-blue", icon: "◈" }
};
function StreamingAnalysisCard({ data }) {
  const cancelStream = useChatStore((s) => s.cancelStream);
  const streamCancel = useChatStore((s) => s.streamCancel);
  const setDraft = useChatStore((s) => s.setDraft);
  const pendingContext = useChatStore((s) => s.pendingContext);
  const clearPendingContext = useChatStore((s) => s.clearPendingContext);
  const port = useChatStore((s) => s.port);
  const bottomRef = reactExports.useRef(null);
  const [followupValue, setFollowupValue] = reactExports.useState("");
  const [followupLoading, setFollowupLoading] = reactExports.useState(false);
  const [followupThread, setFollowupThread] = reactExports.useState([]);
  const [followupError, setFollowupError] = reactExports.useState(null);
  const followupRef = reactExports.useRef(null);
  const {
    symbol,
    exchange,
    analysts = [],
    debate_steps = [],
    synthesis_text = null,
    phase = "analysts",
    report = null,
    trade_plans = null
  } = data ?? {};
  const done = phase === "done";
  const debating = phase === "debate" || phase === "synthesis" || done;
  const synth = phase === "synthesis" || done;
  reactExports.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [analysts.length, debate_steps.length, synthesis_text, done]);
  const running = !done && !!streamCancel;
  const statusLabel = done ? "Analysis" : phase === "analysts" ? "Analysis · Connecting…" : phase === "started" ? "Analysis · Initialising…" : phase === "debate" ? "Analysis · Debate…" : phase === "synthesis" ? "Analysis · Synthesis…" : "Analysis · Running…";
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-elevated border border-blue/30 rounded-xl p-4 max-w-2xl w-full space-y-4 overflow-y-auto max-h-[80vh]", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[11px] uppercase tracking-widest font-ui", children: statusLabel }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-text text-lg font-semibold font-mono mt-0.5", children: [
          symbol,
          " ",
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-muted text-sm font-ui", children: exchange })
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3", children: [
        running && /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: cancelStream,
            className: "text-red text-xs font-ui border border-red/30 rounded-lg px-2.5 py-1\n                         hover:bg-red/10 transition-colors",
            children: "✕ Stop"
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `text-xl ${done ? "" : "animate-pulse"}`, children: "🔬" })
      ] })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "border-t border-border pt-3", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-widest font-ui mb-2", children: "Phase 1 — Analyst Team" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex flex-wrap gap-2 items-start", children: ANALYSTS.map((name) => {
        const result = analysts.find((a) => a.name === name);
        const idx = analysts.findIndex((a) => a.name === name);
        if (!result) {
          const isRunning = !done && (phase === "started" || phase === "analysts");
          return /* @__PURE__ */ jsxRuntimeExports.jsx(
            "span",
            {
              className: `border text-[11px] font-ui px-2.5 py-1 rounded-lg
                             text-subtle border-border/30 bg-transparent
                             ${isRunning ? "animate-pulse opacity-50" : "opacity-25"}`,
              children: DISPLAY_NAMES[name]
            },
            name
          );
        }
        const cls = result.error ? "text-red border-red/30 bg-red/5" : VERDICT_COLOR[result.verdict] ?? VERDICT_COLOR.UNKNOWN;
        return /* @__PURE__ */ jsxRuntimeExports.jsx(AnalystPill, { result, name, idx, cls }, name);
      }) })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "border-t border-border pt-3 grid grid-cols-2 gap-2", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(PhaseLabel, { label: "Phase 2 — Debate", active: debating, done: synth }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(PhaseLabel, { label: "Phase 3 — Synthesis", active: synth, done })
    ] }),
    debate_steps.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "border-t border-border pt-3 space-y-3", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-widest font-ui", children: "Phase 2 — Bull / Bear Debate" }),
      debate_steps.map((s) => {
        const meta = STEP_META[s.step] ?? { label: s.label, color: "text-muted", icon: "•" };
        return /* @__PURE__ */ jsxRuntimeExports.jsx(DebateStep, { meta, text: s.text }, s.step);
      })
    ] }),
    synthesis_text && !done && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "border-t border-border pt-3", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-blue text-[10px] uppercase tracking-widest font-ui mb-2", children: "Phase 3 — Fund Manager Synthesis" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-text text-sm font-ui leading-relaxed whitespace-pre-wrap", children: synthesis_text })
    ] }),
    done && report && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "border-t border-border pt-3", children: /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-text text-sm font-ui leading-relaxed whitespace-pre-wrap", children: report }) }),
    done && trade_plans && Object.entries(trade_plans).filter(([, v2]) => v2 != null).length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx(TradePlans, { plans: trade_plans }),
    done && /* @__PURE__ */ jsxRuntimeExports.jsx(
      ActionChips,
      {
        symbol,
        analysts,
        setDraft,
        onAsk: (q2) => {
          setFollowupValue(q2);
          setTimeout(() => followupRef.current?.focus(), 50);
        }
      }
    ),
    done && /* @__PURE__ */ jsxRuntimeExports.jsx(
      FollowupChat,
      {
        symbol,
        exchange,
        analysts,
        synthesisText: synthesis_text,
        report,
        port,
        value: followupValue,
        setValue: setFollowupValue,
        loading: followupLoading,
        setLoading: setFollowupLoading,
        thread: followupThread,
        setThread: setFollowupThread,
        error: followupError,
        setError: setFollowupError,
        inputRef: followupRef,
        pendingContext,
        clearPendingContext
      }
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { ref: bottomRef })
  ] });
}
function AnalystPill({ result, name, idx, cls }) {
  const [visible, setVisible] = React.useState(false);
  const [expanded, setExpanded] = React.useState(true);
  const hasPoints = result.key_points && result.key_points.length > 0;
  reactExports.useEffect(() => {
    const t2 = setTimeout(() => setVisible(true), idx * 80);
    return () => clearTimeout(t2);
  }, []);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(
    "div",
    {
      className: `border rounded-lg transition-all duration-300 ${cls}
                  ${visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-1"}
                  ${hasPoints ? "cursor-pointer" : ""}`,
      onClick: () => hasPoints && setExpanded((v2) => !v2),
      children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-1.5 px-2.5 py-1", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-[11px] font-ui font-semibold", children: DISPLAY_NAMES[name] }),
          !result.error && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "opacity-60 text-[10px] font-ui", children: [
            result.verdict,
            " ",
            result.confidence,
            "%"
          ] }),
          result.error && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "opacity-60 text-[10px] font-ui", children: "ERR" }),
          hasPoints && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "ml-auto opacity-30 text-[9px] font-mono", children: expanded ? "▴" : "▾" }),
          !hasPoints && result.error && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "ml-auto opacity-30 text-[9px] font-mono text-red", children: "!" })
        ] }),
        expanded && hasPoints && /* @__PURE__ */ jsxRuntimeExports.jsx("ul", { className: "px-2.5 pb-2 space-y-0.5 border-t border-current/10 pt-1.5", children: result.key_points.map((pt, i) => /* @__PURE__ */ jsxRuntimeExports.jsxs("li", { className: "text-[10px] font-ui opacity-80 leading-snug flex gap-1", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "opacity-50 flex-shrink-0", children: "·" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: pt })
        ] }, i)) })
      ]
    }
  );
}
function DebateStep({ meta, text }) {
  const [expanded, setExpanded] = React.useState(false);
  const preview = text.slice(0, 180).replace(/\n/g, " ");
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-panel rounded-lg border border-border overflow-hidden", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs(
      "button",
      {
        onClick: () => setExpanded((v2) => !v2),
        className: "w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-elevated transition-colors",
        children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `text-xs font-mono ${meta.color}`, children: meta.icon }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `text-xs font-ui font-semibold ${meta.color} flex-1`, children: meta.label }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-muted text-[10px] font-mono", children: expanded ? "▴" : "▾" })
        ]
      }
    ),
    !expanded && /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "px-3 pb-2 text-muted text-[11px] font-ui leading-relaxed line-clamp-2", children: [
      preview,
      text.length > 180 ? "…" : ""
    ] }),
    expanded && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "px-3 pb-3 text-text text-xs font-ui leading-relaxed whitespace-pre-wrap border-t border-border pt-2", children: text })
  ] });
}
function PhaseLabel({ label, active, done }) {
  let icon = "○";
  let cls = "text-subtle";
  if (done) {
    icon = "✓";
    cls = "text-green";
  } else if (active) {
    icon = "◆";
    cls = "text-amber animate-pulse";
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: `text-xs font-ui flex items-center gap-1.5 ${cls}`, children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: icon }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: label })
  ] });
}
function TradePlans({ plans }) {
  const entries = Object.entries(plans).filter(([, v2]) => v2 != null);
  if (!entries.length) return null;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "border-t border-border pt-3 space-y-3", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-amber text-[10px] uppercase tracking-widest font-ui", children: "Trade Plans" }),
    entries.map(([name, plan]) => /* @__PURE__ */ jsxRuntimeExports.jsx(TradePlanCard, { name, plan }, name))
  ] });
}
function TradePlanCard({ name, plan }) {
  if (typeof plan === "string") {
    return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-panel rounded-lg p-3 border border-border", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-amber text-xs font-ui uppercase tracking-wider mb-2", children: name }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("pre", { className: "text-text text-xs font-mono whitespace-pre-wrap", children: plan })
    ] });
  }
  const p2 = plan ?? {};
  const exit = p2.exit_plan ?? {};
  const entries = p2.entry_orders ?? [];
  const verdictColor2 = (p2.verdict ?? "").includes("BUY") ? "text-green" : (p2.verdict ?? "").includes("SELL") ? "text-red" : "text-amber";
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-panel rounded-lg p-3 border border-border space-y-2", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-amber text-xs font-ui uppercase tracking-wider", children: name }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: `text-xs font-mono font-semibold ${verdictColor2}`, children: [
        p2.verdict,
        " ",
        p2.confidence ? `${p2.confidence}%` : ""
      ] })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-text text-sm font-semibold", children: p2.strategy_name ?? "—" }),
    entries.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "text-xs font-mono text-muted", children: entries.map((e, i) => /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: `inline-block mr-2 px-1.5 py-0.5 rounded border ${e.action === "BUY" ? "text-green border-green/30" : "text-red border-red/30"}`, children: [
      e.action,
      " ",
      e.quantity,
      "× ",
      e.instrument,
      " @ ",
      e.price ? `₹${Number(e.price).toLocaleString("en-IN")}` : "MKT"
    ] }, i)) }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-4 gap-2 text-[10px] font-mono", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-elevated rounded px-2 py-1", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-muted", children: "Capital" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-text", children: [
          "₹",
          Number(p2.capital_deployed ?? 0).toLocaleString("en-IN", { maximumFractionDigits: 0 }),
          " (",
          Number(p2.capital_pct ?? 0).toFixed(1),
          "%)"
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-elevated rounded px-2 py-1", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-muted", children: "Max Risk" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-red", children: [
          "₹",
          Number(p2.max_risk ?? 0).toLocaleString("en-IN", { maximumFractionDigits: 0 }),
          " (",
          Number(p2.risk_pct ?? 0).toFixed(1),
          "%)"
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-elevated rounded px-2 py-1", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-muted", children: "R:R" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-text", children: [
          Number(p2.reward_risk ?? 0).toFixed(1),
          "×"
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-elevated rounded px-2 py-1", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-muted", children: "Hold" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-text", children: [
          exit.max_hold_days ?? "—",
          "d"
        ] })
      ] })
    ] }),
    (exit.stop_loss || exit.target_1) && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex gap-3 text-[10px] font-mono", children: [
      exit.stop_loss && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-red", children: [
        "SL: ₹",
        Number(exit.stop_loss).toLocaleString("en-IN"),
        " (",
        Number(exit.stop_loss_pct ?? 0).toFixed(1),
        "%)"
      ] }),
      exit.target_1 && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-green", children: [
        "T1: ₹",
        Number(exit.target_1).toLocaleString("en-IN"),
        " (",
        Number(exit.target_1_pct ?? 0).toFixed(1),
        "%)"
      ] }),
      exit.target_2 && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-green", children: [
        "T2: ₹",
        Number(exit.target_2).toLocaleString("en-IN"),
        " (",
        Number(exit.target_2_pct ?? 0).toFixed(1),
        "%)"
      ] })
    ] }),
    p2.rationale?.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "text-[11px] font-ui text-muted space-y-1", children: p2.rationale.map((r2, i) => /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "flex gap-1.5 leading-snug", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-green flex-shrink-0", children: "+" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: r2 })
    ] }, i)) }),
    p2.risks?.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "text-[11px] font-ui text-muted space-y-1", children: p2.risks.map((r2, i) => /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "flex gap-1.5 leading-snug", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-red flex-shrink-0", children: "−" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: r2 })
    ] }, i)) }),
    p2.pre_conditions?.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "text-[10px] font-ui text-amber space-y-0.5 border-t border-border/50 pt-1.5", children: p2.pre_conditions.map((c, i) => /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { children: [
      "⚠ ",
      c
    ] }, i)) })
  ] });
}
function ActionChips({ symbol, analysts, setDraft, onAsk }) {
  const verdictCounts = {};
  for (const a of analysts) {
    const v2 = (a.verdict ?? "").toUpperCase();
    if (v2) verdictCounts[v2] = (verdictCounts[v2] ?? 0) + 1;
  }
  const topVerdict = Object.entries(verdictCounts).sort((a, b) => b[1] - a[1])[0]?.[0] ?? "BULLISH";
  const viewWord = topVerdict === "BEARISH" ? "bearish" : topVerdict === "NEUTRAL" ? "neutral" : "bullish";
  const chips = [
    { label: "🔔 Set alert", action: () => setDraft(`alert ${symbol} RSI below 35`) },
    { label: "📊 Options strategy", action: () => onAsk(`Suggest a specific options strategy for ${symbol} given the ${viewWord} outlook. Include strikes, expiry, and max risk.`) },
    { label: "💰 Entry & target", action: () => onAsk(`What is the ideal entry price, stop-loss, and target for ${symbol} given this analysis?`) },
    { label: "⚠️ Key risks", action: () => onAsk(`What are the biggest risks that could invalidate this ${viewWord} thesis on ${symbol}?`) },
    { label: "🔄 Re-analyze", action: () => setDraft(`analyze ${symbol}`) }
  ];
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "border-t border-border pt-3", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-wider font-ui mb-2", children: "Suggested actions" }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex flex-wrap gap-2", children: chips.map(({ label, action }) => /* @__PURE__ */ jsxRuntimeExports.jsx(
      "button",
      {
        onClick: action,
        className: "text-[11px] font-ui border border-border/60 rounded-lg px-2.5 py-1\n                       text-muted hover:text-text hover:border-border hover:bg-panel\n                       transition-colors",
        children: label
      },
      label
    )) })
  ] });
}
function FollowupChat({
  symbol,
  exchange,
  analysts,
  synthesisText,
  report,
  port,
  value,
  setValue,
  loading,
  setLoading,
  thread,
  setThread,
  error,
  setError,
  inputRef,
  pendingContext,
  clearPendingContext
}) {
  const mountedPendingRef = reactExports.useRef(pendingContext);
  reactExports.useEffect(() => {
    const q2 = (mountedPendingRef.current || "").trim();
    if (!q2 || thread.length > 0 || !port) return;
    clearPendingContext();
    mountedPendingRef.current = "";
    setValue("");
    setError(null);
    setLoading(true);
    setThread([{ q: q2, a: null }]);
    (async () => {
      try {
        const res = await fetch(`http://127.0.0.1:${port}/skills/analyze/followup`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            symbol,
            exchange,
            question: q2,
            session_id: `${symbol}_${exchange}`,
            context: {
              analysts: analysts.map((a) => ({ name: a.name, verdict: a.verdict, confidence: a.confidence, key_points: a.key_points })),
              synthesis_text: synthesisText,
              report
            }
          })
        });
        const json = await res.json();
        const answer = json?.data?.response ?? json?.data ?? "No response";
        setThread([{ q: q2, a: answer }]);
      } catch (e) {
        setThread([]);
        setError("Follow-up failed: " + e.message);
      } finally {
        setLoading(false);
        inputRef.current?.focus();
      }
    })();
  }, [pendingContext, port]);
  async function ask() {
    const q2 = value.trim();
    if (!q2 || loading || !port) return;
    setValue("");
    setError(null);
    setLoading(true);
    try {
      const res = await fetch(`http://127.0.0.1:${port}/skills/analyze/followup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbol,
          exchange,
          question: q2,
          session_id: `${symbol}_${exchange}`,
          context: {
            analysts,
            synthesis_text: synthesisText,
            report
          }
        })
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail?.message ?? json.detail ?? "Request failed");
      const answer = json.data?.response ?? "(no response)";
      setThread((t2) => [...t2, { q: q2, a: answer }]);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }
  function onKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      ask();
    }
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "border-t border-border pt-3 space-y-3", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-blue text-[10px] uppercase tracking-widest font-ui", children: "Follow-up" }),
    thread.map(({ q: q2, a }, i) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-1.5", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex gap-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-muted text-[10px] font-mono mt-0.5 flex-shrink-0", children: "you" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-text text-[12px] font-ui", children: q2 })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex gap-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-blue text-[10px] font-mono mt-0.5 flex-shrink-0", children: "ai" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-text text-[12px] font-ui leading-relaxed whitespace-pre-wrap", children: a })
      ] })
    ] }, i)),
    loading && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex gap-2 items-start bg-blue/5 border border-blue/20 rounded-lg px-3 py-2", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-blue text-[10px] font-mono mt-0.5 flex-shrink-0", children: "ai" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-1.5", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-blue text-[11px] font-ui", children: "Thinking" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "flex gap-0.5", children: [0, 1, 2].map((i) => /* @__PURE__ */ jsxRuntimeExports.jsx(
          "span",
          {
            className: "w-1 h-1 rounded-full bg-blue animate-bounce",
            style: { animationDelay: `${i * 0.15}s` }
          },
          i
        )) })
      ] })
    ] }),
    error && /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-red text-[11px] font-ui", children: [
      "⚠ ",
      error
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 bg-panel border border-border rounded-lg px-3 py-2", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "input",
        {
          ref: inputRef,
          type: "text",
          value,
          onChange: (e) => setValue(e.target.value),
          onKeyDown,
          placeholder: `Ask about ${symbol}…`,
          disabled: loading,
          className: "flex-1 bg-transparent text-text text-[12px] font-mono outline-none\n                     placeholder:text-subtle disabled:opacity-50"
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "button",
        {
          onClick: ask,
          disabled: !value.trim() || loading,
          className: "text-blue text-[11px] font-mono disabled:opacity-30 hover:opacity-80 transition-opacity",
          children: "↵"
        }
      )
    ] })
  ] });
}
function BacktestCard({ data }) {
  if (!data) return null;
  const r2 = data;
  const metrics = [
    ["Total Return", pct$1(r2.total_return)],
    ["CAGR", pct$1(r2.cagr)],
    ["Sharpe", num(r2.sharpe_ratio ?? r2.sharpe)],
    ["Max Drawdown", pct$1(r2.max_drawdown)],
    ["Win Rate", pct$1(r2.win_rate)],
    ["Total Trades", r2.total_trades ?? "—"],
    ["Profit Factor", num(r2.profit_factor)],
    ["Avg Hold", r2.avg_hold_days ? `${r2.avg_hold_days}d` : "—"]
  ];
  const returnVal = Number(r2.total_return ?? 0);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-elevated border border-border rounded-xl p-4 max-w-lg w-full", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-start justify-between mb-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[11px] uppercase tracking-widest font-ui mb-1", children: "Backtest" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-text text-lg font-semibold font-mono", children: [
          r2.symbol,
          " ",
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-muted text-sm", children: "·" }),
          " ",
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-amber text-sm", children: r2.strategy })
        ] }),
        r2.period && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-xs font-ui mt-0.5", children: r2.period })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: `text-2xl font-mono font-bold ${returnVal >= 0 ? "text-green" : "text-red"}`, children: [
        returnVal >= 0 ? "+" : "",
        pct$1(returnVal)
      ] })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid grid-cols-4 gap-3 border-t border-border pt-3", children: metrics.map(([label, val]) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-wider font-ui", children: label }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-text text-sm font-mono mt-0.5", children: val })
    ] }, label)) })
  ] });
}
const pct$1 = (n2) => `${Number(n2 ?? 0).toFixed(2)}%`;
const num = (n2) => Number(n2 ?? 0).toFixed(2);
function FlowsCard({ data }) {
  if (!data) return null;
  const fii = Number(data.fii_net_today ?? 0);
  const dii = Number(data.dii_net_today ?? 0);
  const fii5 = Number(data.fii_5d_net ?? 0);
  const dii5 = Number(data.dii_5d_net ?? 0);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-elevated border border-border rounded-xl p-4 max-w-md w-full", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 mb-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: "🌊" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[11px] uppercase tracking-widest font-ui", children: "FII / DII Flows" })
    ] }),
    data.signal && /* @__PURE__ */ jsxRuntimeExports.jsx(Signal$1, { value: data.signal, reason: data.signal_reason }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-2 gap-3 mt-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(FlowBox, { label: "FII Today", value: fii, streak: data.fii_streak }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(FlowBox, { label: "DII Today", value: dii, streak: data.dii_streak }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(FlowBox, { label: "FII 5-Day", value: fii5 }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(FlowBox, { label: "DII 5-Day", value: dii5 })
    ] }),
    data.divergence && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "mt-3 pt-3 border-t border-border text-xs font-ui text-muted", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-amber font-semibold", children: "Divergence: " }),
      data.divergence
    ] })
  ] });
}
function FlowBox({ label, value, streak }) {
  const pos = value >= 0;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-panel rounded-lg p-3 border border-border", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-wider font-ui mb-1", children: label }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: `font-mono text-base font-semibold ${pos ? "text-green" : "text-red"}`, children: [
      pos ? "+" : "",
      "₹",
      Math.abs(value).toFixed(0),
      " Cr"
    ] }),
    streak !== void 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-muted text-[10px] font-ui mt-0.5", children: [
      Math.abs(streak),
      "d ",
      streak >= 0 ? "buying" : "selling"
    ] })
  ] });
}
function Signal$1({ value, reason }) {
  const color = value === "BULLISH" ? "text-green border-green/30 bg-green/5" : value === "BEARISH" ? "text-red border-red/30 bg-red/5" : "text-muted border-border";
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: `inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border text-sm font-ui ${color}`, children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "font-semibold", children: value }),
    reason && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-muted text-xs", children: [
      "— ",
      reason
    ] })
  ] });
}
function MorningBriefCard({ data }) {
  if (!data) return null;
  const { market_snapshot, institutional_flows, top_news, market_breadth } = data;
  const setDraft = useChatStore((s) => s.setDraft);
  const posture = market_snapshot?.posture ?? null;
  const niftyLtp = market_snapshot?.nifty?.ltp ?? null;
  const niftyChg = market_snapshot?.nifty?.change_pct ?? null;
  const vix = market_snapshot?.vix?.ltp ?? null;
  const fiiNet = institutional_flows?.fii_net_today ?? null;
  const fiiStreak = institutional_flows?.fii_streak ?? null;
  const advances = market_breadth?.advances ?? null;
  const declines = market_breadth?.declines ?? null;
  const ctx = [
    posture && `Market posture: ${posture}`,
    niftyLtp && `NIFTY at ${Number(niftyLtp).toLocaleString("en-IN")} (${niftyChg != null ? (niftyChg >= 0 ? "+" : "") + Number(niftyChg).toFixed(2) + "%" : ""})`,
    vix && `VIX at ${Number(vix).toFixed(1)}`,
    fiiNet && `FII net ${Number(fiiNet) >= 0 ? "+" : ""}₹${Number(fiiNet).toFixed(0)} Cr${fiiStreak != null ? ` (${Math.abs(fiiStreak)}d ${Number(fiiStreak) >= 0 ? "buying" : "selling"})` : ""}`,
    advances && declines && `Breadth: ${advances} advances, ${declines} declines`
  ].filter(Boolean).join("; ");
  const chips = [
    posture && {
      label: `${posture === "BULLISH" ? "📈" : posture === "BEARISH" ? "📉" : "⚡"} ${posture} market — how to trade today?`,
      q: `${ctx}. Given this ${posture.toLowerCase()} market setup, what should I focus on today — key levels to watch, sectors to favour, and positions to avoid?`
    },
    fiiNet != null && {
      label: `FII ${Number(fiiNet) >= 0 ? "buying" : "selling"} ₹${Math.abs(Number(fiiNet)).toFixed(0)} Cr — what does this mean?`,
      q: `${ctx}. What does this FII flow pattern mean for NIFTY tomorrow and which sectors are most impacted?`
    },
    advances != null && declines != null && {
      label: `${advances} up vs ${declines} down — oversold or more downside?`,
      q: `${ctx}. Is this breadth reading a sign of exhaustion and potential reversal, or does it suggest more downside ahead?`
    },
    top_news?.length > 0 && {
      label: "📰 What's the biggest market risk today?",
      q: `${ctx}. Top news: ${top_news.slice(0, 3).map((n2) => n2.headline ?? n2.title ?? "").filter(Boolean).join(" | ")}. What is the single biggest risk to watch today?`
    }
  ].filter(Boolean);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-elevated border border-amber/30 rounded-xl p-4 max-w-2xl w-full space-y-4", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-lg", children: "☀️" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-amber text-[11px] uppercase tracking-widest font-ui", children: "Morning Brief" })
    ] }),
    market_snapshot && /* @__PURE__ */ jsxRuntimeExports.jsxs(Section$1, { title: "Markets", children: [
      market_snapshot.posture && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "mb-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(Signal, { value: market_snapshot.posture }),
        market_snapshot.posture_reason && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-xs font-ui mt-1", children: market_snapshot.posture_reason })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid grid-cols-2 gap-3", children: ["nifty", "banknifty", "sensex", "vix"].map((key) => {
        const idx = market_snapshot[key];
        if (!idx || typeof idx !== "object") return null;
        const pos = (idx.change_pct ?? 0) >= 0;
        return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-panel rounded-lg p-2.5 border border-border", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-wider font-ui", children: key }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-text text-sm font-mono font-semibold mt-0.5", children: Number(idx.ltp ?? 0).toLocaleString("en-IN", { maximumFractionDigits: 2 }) }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: `text-xs font-mono ${pos ? "text-green" : "text-red"}`, children: [
            pos ? "+" : "",
            Number(idx.change_pct ?? 0).toFixed(2),
            "%"
          ] })
        ] }, key);
      }) })
    ] }),
    institutional_flows && /* @__PURE__ */ jsxRuntimeExports.jsxs(Section$1, { title: "FII / DII", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-2 gap-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(FlowStat, { label: "FII Today", value: institutional_flows.fii_net_today, streak: institutional_flows.fii_streak }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(FlowStat, { label: "DII Today", value: institutional_flows.dii_net_today, streak: institutional_flows.dii_streak })
      ] }),
      institutional_flows.signal && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mt-2", children: /* @__PURE__ */ jsxRuntimeExports.jsx(Signal, { value: institutional_flows.signal, reason: institutional_flows.signal_reason }) })
    ] }),
    top_news?.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx(Section$1, { title: "Top News", children: /* @__PURE__ */ jsxRuntimeExports.jsx("ul", { className: "space-y-2", children: top_news.slice(0, 5).map((n2, i) => /* @__PURE__ */ jsxRuntimeExports.jsxs("li", { className: "flex gap-2 text-xs font-ui text-text leading-snug", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-muted flex-shrink-0", children: "•" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: n2.headline ?? n2.title ?? String(n2) })
    ] }, i)) }) }),
    market_breadth && /* @__PURE__ */ jsxRuntimeExports.jsx(Section$1, { title: "Breadth", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex gap-4 text-xs font-mono", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-green", children: [
        "▲ ",
        market_breadth.advances ?? "—"
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-red", children: [
        "▼ ",
        market_breadth.declines ?? "—"
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-muted", children: [
        "— ",
        market_breadth.unchanged ?? "—"
      ] })
    ] }) }),
    chips.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex flex-wrap gap-2 pt-1 border-t border-border", children: chips.map((chip) => /* @__PURE__ */ jsxRuntimeExports.jsx(
      "button",
      {
        onClick: () => setDraft(chip.q),
        className: "text-[11px] font-ui px-3 py-1.5 rounded-full border border-border\n                         text-muted hover:text-text hover:border-amber/50 hover:bg-amber/5\n                         transition-colors cursor-pointer",
        children: chip.label
      },
      chip.label
    )) })
  ] });
}
function Section$1({ title, children }) {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "border-t border-border pt-3", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-widest font-ui mb-2", children: title }),
    children
  ] });
}
function FlowStat({ label, value, streak }) {
  const v2 = Number(value ?? 0);
  const pos = v2 >= 0;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-panel rounded-lg p-2.5 border border-border", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] font-ui", children: label }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: `font-mono text-sm font-semibold mt-0.5 ${pos ? "text-green" : "text-red"}`, children: [
      pos ? "+" : "",
      "₹",
      Math.abs(v2).toFixed(0),
      " Cr"
    ] }),
    streak !== void 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-muted text-[10px] font-ui mt-0.5", children: [
      Math.abs(streak),
      "d ",
      streak >= 0 ? "buying" : "selling"
    ] })
  ] });
}
function Signal({ value, reason }) {
  const color = value === "BULLISH" ? "text-green border-green/30 bg-green/5" : value === "BEARISH" ? "text-red border-red/30 bg-red/5" : value === "VOLATILE" ? "text-amber border-amber/30 bg-amber/5" : "text-muted border-border";
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: `inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-xs font-ui ${color}`, children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "font-semibold", children: value }),
    reason && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-muted", children: [
      "— ",
      reason
    ] })
  ] });
}
function HoldingsCard({ data }) {
  const holdings = Array.isArray(data) ? data : data?.holdings ?? [];
  if (!holdings.length) {
    return /* @__PURE__ */ jsxRuntimeExports.jsx(Card, { title: "Holdings", children: /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-sm font-ui", children: "No holdings found." }) });
  }
  const totalInvested = holdings.reduce((s, h) => s + (h.avg_price ?? 0) * (h.quantity ?? 0), 0);
  const totalCurrent = holdings.reduce((s, h) => s + (h.last_price ?? h.ltp ?? 0) * (h.quantity ?? 0), 0);
  const totalPnl = holdings.reduce((s, h) => s + Number(h.pnl ?? h.unrealised_pnl ?? 0), 0);
  const totalDayChg = holdings.reduce((s, h) => s + Number(h.day_change ?? 0) * (h.quantity ?? 1), 0);
  const overallPct = totalInvested > 0 ? totalPnl / totalInvested * 100 : 0;
  const dayPct = totalCurrent > 0 ? totalDayChg / (totalCurrent - totalDayChg) * 100 : 0;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(Card, { title: "Holdings", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-3 gap-3 mb-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        SummaryBox,
        {
          label: "Invested",
          value: `₹${totalInvested.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        SummaryBox,
        {
          label: "Overall P&L",
          value: `${totalPnl >= 0 ? "+" : ""}₹${totalPnl.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`,
          sub: `${overallPct >= 0 ? "+" : ""}${overallPct.toFixed(2)}%`,
          positive: totalPnl >= 0
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        SummaryBox,
        {
          label: "Today's P&L",
          value: `${totalDayChg >= 0 ? "+" : ""}₹${totalDayChg.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`,
          sub: `${dayPct >= 0 ? "+" : ""}${dayPct.toFixed(2)}%`,
          positive: totalDayChg >= 0
        }
      )
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("table", { className: "w-full text-sm font-mono", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("thead", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "text-muted text-[10px] uppercase tracking-wider border-b border-border", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left pb-2", children: "Symbol" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-right pb-2", children: "Qty" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-right pb-2", children: "Avg" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-right pb-2", children: "LTP" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-right pb-2", children: "P&L" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-right pb-2", children: "Today" })
      ] }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { children: holdings.map((h, i) => {
        const pnl = Number(h.pnl ?? h.unrealised_pnl ?? 0);
        const pnlPct = Number(h.pnl_pct ?? 0);
        const dayChg = Number(h.day_change ?? 0);
        const dayChgPct = Number(h.day_change_pct ?? 0);
        return /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "border-b border-border/50 last:border-0", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "py-2 text-text font-semibold", children: h.symbol ?? h.tradingsymbol }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "py-2 text-right text-text", children: h.quantity ?? h.qty }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("td", { className: "py-2 text-right text-muted", children: [
            "₹",
            Number(h.avg_price ?? h.average_price ?? 0).toFixed(2)
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("td", { className: "py-2 text-right text-text", children: [
            "₹",
            Number(h.ltp ?? h.last_price ?? 0).toFixed(2)
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("td", { className: `py-2 text-right ${pnl >= 0 ? "text-green" : "text-red"}`, children: [
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
              pnl >= 0 ? "+" : "",
              "₹",
              Number(pnl).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 })
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "text-[10px]", children: [
              pnlPct >= 0 ? "+" : "",
              pnlPct.toFixed(2),
              "%"
            ] })
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("td", { className: `py-2 text-right ${dayChg >= 0 ? "text-green" : "text-red"}`, children: [
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
              dayChg >= 0 ? "+" : "",
              "₹",
              Number(dayChg).toLocaleString("en-IN", { maximumFractionDigits: 0 })
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "text-[10px]", children: [
              dayChgPct >= 0 ? "+" : "",
              dayChgPct.toFixed(2),
              "%"
            ] })
          ] })
        ] }, i);
      }) })
    ] })
  ] });
}
function SummaryBox({ label, value, sub, positive }) {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-panel rounded-lg p-2.5 border border-border", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-wider font-ui", children: label }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: `text-sm font-mono font-semibold mt-0.5 ${positive != null ? positive ? "text-green" : "text-red" : "text-text"}`, children: value }),
    sub && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: `text-[10px] font-mono mt-0.5 ${positive != null ? positive ? "text-green" : "text-red" : "text-muted"}`, children: sub })
  ] });
}
function Card({ title, children }) {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[11px] uppercase tracking-widest font-ui mb-3", children: title }),
    children
  ] });
}
function extractText(data) {
  if (typeof data === "string") return data;
  if (data?.response) return data.response;
  if (data?.text) return data.text;
  if (data?.result) return data.result;
  return JSON.stringify(data, null, 2);
}
function renderInline(text) {
  const parts = [];
  const re2 = /\*\*(.+?)\*\*|`(.+?)`/g;
  let last = 0;
  let match;
  while ((match = re2.exec(text)) !== null) {
    if (match.index > last) parts.push(text.slice(last, match.index));
    if (match[1] != null) parts.push(/* @__PURE__ */ jsxRuntimeExports.jsx("strong", { className: "font-semibold text-text", children: match[1] }, match.index));
    if (match[2] != null) parts.push(/* @__PURE__ */ jsxRuntimeExports.jsx("code", { className: "font-mono text-amber bg-panel px-1 rounded text-[10px]", children: match[2] }, match.index));
    last = re2.lastIndex;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts;
}
function renderBlock(line, idx) {
  if (line.startsWith("### ")) {
    return /* @__PURE__ */ jsxRuntimeExports.jsx("h3", { className: "text-text text-[12px] font-semibold font-ui mt-3 mb-1 uppercase tracking-wide text-muted", children: renderInline(line.slice(4)) }, idx);
  }
  if (line.startsWith("## ")) {
    return /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-text text-[14px] font-bold font-ui mt-4 mb-1.5", children: renderInline(line.slice(3)) }, idx);
  }
  if (line.startsWith("# ")) {
    return /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-text text-[16px] font-bold font-ui mt-4 mb-2", children: renderInline(line.slice(2)) }, idx);
  }
  if (/^---+$/.test(line.trim())) {
    return /* @__PURE__ */ jsxRuntimeExports.jsx("hr", { className: "border-border my-3" }, idx);
  }
  if (line.startsWith("- ") || line.startsWith("* ")) {
    return /* @__PURE__ */ jsxRuntimeExports.jsxs("li", { className: "flex gap-2 text-text text-[13px] font-ui leading-relaxed", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-muted flex-shrink-0 mt-0.5", children: "·" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: renderInline(line.slice(2)) })
    ] }, idx);
  }
  if (line.trim() === "") {
    return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "h-2" }, idx);
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-text text-[13px] font-ui leading-relaxed", children: renderInline(line) }, idx);
}
function MarkdownCard({ data }) {
  const raw = extractText(data);
  const text = raw.replace(/\\n/g, "\n").replace(/\\t/g, "	");
  const lines = text.split("\n");
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "bg-elevated border border-border rounded-xl px-5 py-4 max-w-2xl w-full", children: /* @__PURE__ */ jsxRuntimeExports.jsx("ul", { className: "list-none space-y-0.5", children: lines.map((line, i) => renderBlock(line, i)) }) });
}
function ErrorCard({ text }) {
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "bg-elevated border border-red/40 rounded-xl px-4 py-3 max-w-lg", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-start gap-2", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-red text-sm mt-0.5", children: "✕" }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-red text-sm font-ui leading-relaxed", children: text })
  ] }) });
}
function fmt$4(n2) {
  return Number(n2 ?? 0).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function FundsCard({ data }) {
  const d = data?.data ?? data ?? {};
  const demo = d.demo ?? false;
  const rows = [
    { label: "Available Cash", value: d.available_cash ?? d.equity?.net ?? 0, color: "text-green" },
    { label: "Used Margin", value: d.used_margin ?? d.equity?.utilised?.debits ?? 0, color: "text-red" },
    { label: "Total Balance", value: d.total_balance ?? d.equity?.available?.live_balance ?? 0, color: "text-text" }
  ];
  const total = rows[2].value;
  const used = rows[1].value;
  const usedPct = total > 0 ? Math.min(used / total * 100, 100) : 0;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-elevated border border-border rounded-xl p-4 max-w-sm w-full space-y-4", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-widest font-ui", children: "Account Funds" }),
      demo && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-amber text-[10px] font-ui border border-amber/30 px-1.5 py-0.5 rounded", children: "demo" })
    ] }),
    rows.map(({ label, value, color }) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-muted text-[12px] font-ui", children: label }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: `text-[13px] font-mono font-semibold ${color}`, children: [
        "₹",
        fmt$4(value)
      ] })
    ] }, label)),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex justify-between mb-1", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-muted text-[10px] font-ui", children: "Margin used" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-muted text-[10px] font-mono", children: [
          usedPct.toFixed(1),
          "%"
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "w-full bg-panel rounded-full h-1.5", children: /* @__PURE__ */ jsxRuntimeExports.jsx(
        "div",
        {
          className: `h-1.5 rounded-full transition-all ${usedPct > 80 ? "bg-red" : usedPct > 50 ? "bg-amber" : "bg-green"}`,
          style: { width: `${usedPct}%` }
        }
      ) })
    ] })
  ] });
}
function ProfileCard({ data }) {
  const d = data?.data ?? data ?? {};
  const demo = d.demo ?? false;
  const fields = [
    { label: "Name", value: d.name ?? d.user_name ?? "—" },
    { label: "Client ID", value: d.client_id ?? d.user_id ?? "—" },
    { label: "Email", value: d.email ?? "—" },
    { label: "Broker", value: d.broker ?? d.broker_name ?? "—" },
    { label: "Exchanges", value: Array.isArray(d.exchanges) ? d.exchanges.join(", ") : d.exchanges ?? "—" }
  ];
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-elevated border border-border rounded-xl p-4 max-w-sm w-full space-y-3", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-widest font-ui", children: "Account Profile" }),
      demo && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-amber text-[10px] font-ui border border-amber/30 px-1.5 py-0.5 rounded", children: "demo" })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "space-y-2.5", children: fields.map(({ label, value }) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-start justify-between gap-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-muted text-[11px] font-ui flex-shrink-0", children: label }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-text text-[12px] font-ui text-right truncate", children: value })
    ] }, label)) })
  ] });
}
const STATUS_COLOR = {
  COMPLETE: "text-green",
  REJECTED: "text-red",
  CANCELLED: "text-muted",
  PENDING: "text-amber",
  OPEN: "text-blue",
  TRIGGER_PENDING: "text-amber"
};
function OrdersCard({ data }) {
  const d = data?.data ?? data ?? {};
  const orders = d.orders ?? (Array.isArray(data) ? data : []);
  const demo = d.demo ?? false;
  if (!orders.length) {
    return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-widest font-ui mb-3", children: "Today's Orders" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-sm font-ui", children: demo ? "No orders (demo mode — connect a broker)" : "No orders today." })
    ] });
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between mb-3", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-widest font-ui", children: "Today's Orders" }),
      demo && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-amber text-[10px] font-ui border border-amber/30 px-1.5 py-0.5 rounded", children: "demo" })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("table", { className: "w-full text-sm font-mono", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("thead", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "text-muted text-[10px] uppercase tracking-wider border-b border-border", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left pb-2", children: "Symbol" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left pb-2", children: "Type" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-right pb-2", children: "Qty" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-right pb-2", children: "Price" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-right pb-2", children: "Status" })
      ] }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { children: orders.map((o, i) => {
        const status = (o.status ?? o.order_status ?? "UNKNOWN").toUpperCase();
        const isBuy = (o.transaction_type ?? o.side ?? "").toUpperCase() === "BUY";
        return /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "border-b border-border/50 last:border-0", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "py-2 text-text font-semibold", children: o.symbol ?? o.tradingsymbol ?? "—" }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("td", { className: `py-2 text-[11px] ${isBuy ? "text-green" : "text-red"}`, children: [
            (o.transaction_type ?? o.side ?? "—").toUpperCase(),
            " ",
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-muted", children: o.order_type ?? o.type ?? "" })
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "py-2 text-right text-text", children: o.quantity ?? o.qty ?? "—" }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("td", { className: "py-2 text-right text-text", children: [
            "₹",
            Number(o.price ?? o.average_price ?? 0).toFixed(2)
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: `py-2 text-right text-[11px] ${STATUS_COLOR[status] ?? "text-muted"}`, children: status })
        ] }, i);
      }) })
    ] })
  ] });
}
function AlertsCard({ data }) {
  const port = useChatStore((s) => s.port);
  const d = data?.data ?? data ?? {};
  const [alerts, setAlerts] = reactExports.useState(d.alerts ?? d.active_alerts ?? (Array.isArray(data) ? data : []));
  const [removing, setRemoving] = reactExports.useState(null);
  async function remove(alertId) {
    setRemoving(alertId);
    try {
      await fetch(`http://127.0.0.1:${port}/skills/alerts/remove`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ alert_id: alertId })
      });
      setAlerts((prev) => prev.filter((a) => (a.id ?? a.alert_id) !== alertId));
    } catch (_) {
    }
    setRemoving(null);
  }
  if (!alerts.length) {
    return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-widest font-ui mb-3", children: "Alerts" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-muted text-sm font-ui", children: [
        "No active alerts. Use ",
        /* @__PURE__ */ jsxRuntimeExports.jsx("code", { className: "font-mono text-amber", children: "alert SYMBOL above/below PRICE" }),
        " to add one."
      ] })
    ] });
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-muted text-[10px] uppercase tracking-widest font-ui mb-3", children: [
      "Alerts ",
      /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-subtle", children: [
        "(",
        alerts.length,
        ")"
      ] })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "space-y-2", children: alerts.map((a) => {
      const id2 = a.id ?? a.alert_id ?? String(Math.random());
      const symbol = a.symbol ?? "—";
      const condition = a.condition ?? a.description ?? "—";
      const threshold = a.threshold != null ? `₹${Number(a.threshold).toLocaleString("en-IN")}` : "";
      const triggered = a.triggered ?? false;
      return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: `flex items-center justify-between rounded-lg border px-3 py-2
              ${triggered ? "border-green/40 bg-green/5" : "border-border bg-panel"}`, children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "min-w-0", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-text text-[12px] font-mono font-semibold", children: symbol }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `text-[10px] font-ui ${triggered ? "text-green" : "text-muted"}`, children: triggered ? "✓ triggered" : "● active" })
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-muted text-[11px] font-ui mt-0.5 truncate", children: [
            condition,
            " ",
            threshold
          ] })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: () => remove(id2),
            disabled: removing === id2,
            className: "ml-3 text-subtle hover:text-red text-[11px] font-ui transition-colors\n                           disabled:opacity-40 flex-shrink-0",
            children: removing === id2 ? "…" : "✕"
          }
        )
      ] }, id2);
    }) })
  ] });
}
function fmt$3(n2) {
  return Number(n2 ?? 0).toLocaleString("en-IN");
}
function OICard({ data }) {
  const d = data?.data ?? data ?? {};
  const symbol = d.symbol ?? "—";
  const spot = d.spot ?? d.spot_price ?? 0;
  const pcr = d.pcr ?? d.put_call_ratio ?? null;
  const maxPain = d.max_pain ?? d.resistance ?? null;
  const support = d.support ?? null;
  const chain = d.chain ?? [];
  const topStrikes = chain.sort((a, b) => b.ce_oi + b.pe_oi - (a.ce_oi + a.pe_oi)).slice(0, 10).sort((a, b) => a.strike - b.strike);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full space-y-4", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-widest font-ui", children: "OI Profile" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-text text-lg font-mono font-semibold mt-0.5", children: symbol })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "text-right space-y-1", children: [
        spot > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-text text-sm font-mono", children: [
          "Spot ₹",
          Number(spot).toLocaleString("en-IN")
        ] }),
        pcr != null && /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: `text-[12px] font-ui ${pcr > 1.2 ? "text-green" : pcr < 0.8 ? "text-red" : "text-amber"}`, children: [
          "PCR ",
          Number(pcr).toFixed(2)
        ] })
      ] })
    ] }),
    (maxPain || support) && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-2 gap-3 border border-border rounded-lg p-3", children: [
      maxPain && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] font-ui uppercase tracking-wider", children: "Max Pain / Resistance" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-red text-[13px] font-mono mt-0.5", children: [
          "₹",
          Number(maxPain).toLocaleString("en-IN")
        ] })
      ] }),
      support && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] font-ui uppercase tracking-wider", children: "Support (Max Put OI)" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-green text-[13px] font-mono mt-0.5", children: [
          "₹",
          Number(support).toLocaleString("en-IN")
        ] })
      ] })
    ] }),
    topStrikes.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("table", { className: "w-full text-[11px] font-mono", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("thead", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "text-muted uppercase tracking-wider border-b border-border", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-right pb-2", children: "CE OI" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-center pb-2 text-text", children: "Strike" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left pb-2", children: "PE OI" })
      ] }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { children: topStrikes.map((row, i) => {
        const atm = spot > 0 && Math.abs(row.strike - spot) < (topStrikes[1]?.strike - topStrikes[0]?.strike) / 2;
        return /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: `border-b border-border/40 last:border-0 ${atm ? "bg-amber/5" : ""}`, children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "py-1 text-right text-red", children: fmt$3(row.ce_oi) }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: `py-1 text-center font-semibold ${atm ? "text-amber" : "text-text"}`, children: Number(row.strike).toLocaleString("en-IN") }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "py-1 text-left text-green", children: fmt$3(row.pe_oi) })
        ] }, i);
      }) })
    ] })
  ] });
}
const IMPACT_COLOR = {
  high: "text-red border-red/30 bg-red/5",
  medium: "text-amber border-amber/30 bg-amber/5",
  low: "text-muted border-border",
  bullish: "text-green border-green/30 bg-green/5",
  bearish: "text-red border-red/30 bg-red/5"
};
function PatternsCard({ data }) {
  const d = data?.data ?? data ?? {};
  const patterns = d.patterns ?? d.active_patterns ?? (Array.isArray(data) ? data : []);
  if (!patterns.length) {
    return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-widest font-ui mb-2", children: "Active Patterns" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-sm font-ui", children: "No active patterns detected." })
    ] });
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full space-y-3", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-muted text-[10px] uppercase tracking-widest font-ui", children: [
      "Active Patterns ",
      /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-subtle", children: [
        "(",
        patterns.length,
        ")"
      ] })
    ] }),
    patterns.map((p2, i) => {
      const impact = (p2.impact ?? p2.direction ?? "medium").toLowerCase();
      const cls = IMPACT_COLOR[impact] ?? IMPACT_COLOR.medium;
      return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: `border rounded-lg p-3 ${cls}`, children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between mb-1", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-[12px] font-ui font-semibold", children: p2.name ?? p2.pattern ?? "—" }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
            p2.confidence != null && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-[10px] font-ui opacity-70", children: [
              p2.confidence,
              "% conf"
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `text-[10px] font-ui uppercase border rounded px-1.5 py-0.5 ${cls}`, children: impact })
          ] })
        ] }),
        (p2.description ?? p2.action) && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-[11px] font-ui opacity-80 leading-relaxed", children: p2.description ?? p2.action })
      ] }, i);
    })
  ] });
}
function Metric({ label, value, hint }) {
  const v2 = Number(value ?? 0);
  const colored = label === "Delta" ? v2 > 0 ? "text-green" : v2 < 0 ? "text-red" : "text-text" : label === "Theta" ? "text-red" : "text-text";
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-panel rounded-lg p-3 border border-border", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-wider font-ui", children: label }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: `text-[16px] font-mono font-semibold mt-1 ${colored}`, children: [
      v2 >= 0 && label !== "IV" ? "+" : "",
      v2.toFixed(2)
    ] }),
    hint && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-subtle text-[10px] font-ui mt-0.5", children: hint })
  ] });
}
function GreeksCard({ data }) {
  const d = data?.data ?? data ?? {};
  const demo = d.demo ?? false;
  const net = d.net ?? d.portfolio_greeks ?? {};
  const metrics = [
    { label: "Delta", value: net.delta ?? net.net_delta ?? 0, hint: "Portfolio directional exposure" },
    { label: "Theta", value: net.theta ?? net.net_theta ?? 0, hint: "Daily time decay (₹)" },
    { label: "Vega", value: net.vega ?? net.net_vega ?? 0, hint: "IV sensitivity" },
    { label: "Gamma", value: net.gamma ?? net.net_gamma ?? 0, hint: "Delta change rate" }
  ];
  const warnings = d.warnings ?? d.risk_warnings ?? [];
  const positions = d.positions ?? d.by_position ?? [];
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full space-y-4", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-widest font-ui", children: "Portfolio Greeks" }),
      demo && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-amber text-[10px] font-ui border border-amber/30 px-1.5 py-0.5 rounded", children: "demo" })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid grid-cols-4 gap-2", children: metrics.map((m2) => /* @__PURE__ */ jsxRuntimeExports.jsx(Metric, { ...m2 }, m2.label)) }),
    warnings.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "space-y-1", children: warnings.map((w2, i) => /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-amber text-[11px] font-ui flex gap-1.5", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: "⚠" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: typeof w2 === "string" ? w2 : w2.message ?? JSON.stringify(w2) })
    ] }, i)) }),
    positions.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "border-t border-border pt-3", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-wider font-ui mb-2", children: "By Position" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("table", { className: "w-full text-[11px] font-mono", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("thead", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "text-muted border-b border-border", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left pb-1.5", children: "Symbol" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-right pb-1.5", children: "Δ Delta" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-right pb-1.5", children: "Θ Theta" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-right pb-1.5", children: "ν Vega" })
        ] }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { children: positions.map((p2, i) => /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "border-b border-border/40 last:border-0", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "py-1.5 text-text", children: p2.symbol ?? p2.underlying ?? "—" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: `py-1.5 text-right ${Number(p2.delta ?? 0) >= 0 ? "text-green" : "text-red"}`, children: Number(p2.delta ?? 0).toFixed(2) }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "py-1.5 text-right text-red", children: Number(p2.theta ?? 0).toFixed(2) }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "py-1.5 text-right text-text", children: Number(p2.vega ?? 0).toFixed(2) })
        ] }, i)) })
      ] })
    ] })
  ] });
}
function Section({ title, items, color }) {
  if (!items?.length) return null;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: `text-[10px] uppercase tracking-widest font-ui mb-2 ${color}`, children: title }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex flex-wrap gap-1.5", children: items.map((item, i) => {
      const symbol = typeof item === "string" ? item : item.symbol ?? item.tradingsymbol ?? JSON.stringify(item);
      const detail = typeof item === "object" ? item.iv_rank != null ? `IV ${item.iv_rank}%` : item.oi_change != null ? `OI +${item.oi_change}%` : "" : "";
      return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: `border rounded-lg px-2.5 py-1.5 ${color.replace("text-", "border-").replace("500", "400")}/30 bg-current/5`, children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `text-[12px] font-mono font-semibold ${color}`, children: symbol }),
        detail && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-[10px] font-ui text-muted ml-1.5", children: detail })
      ] }, i);
    }) })
  ] });
}
function ScanCard({ data }) {
  const d = data?.data ?? data ?? {};
  const summary = d.summary ?? d.scan_summary ?? null;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full space-y-4", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-widest font-ui", children: "Options Scan" }),
    summary && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[12px] font-ui", children: summary }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(Section, { title: "High IV", items: d.high_iv, color: "text-red" }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(Section, { title: "Unusual OI", items: d.unusual_oi, color: "text-amber" }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(Section, { title: "High Put Writing", items: d.high_put_writing, color: "text-green" }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(Section, { title: "Opportunities", items: d.opportunities ?? d.results, color: "text-blue" }),
    !d.high_iv?.length && !d.unusual_oi?.length && !d.high_put_writing?.length && !d.results?.length && /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-muted text-sm font-ui", children: [
      "No scan results. Run: ",
      /* @__PURE__ */ jsxRuntimeExports.jsx("code", { className: "font-mono text-amber", children: "scan" })
    ] })
  ] });
}
const ENTITY_COLOR = {
  FII: "text-blue",
  MF: "text-amber",
  DII: "text-purple-400",
  PROMOTER: "text-green",
  OTHER: "text-muted"
};
function fmt$2(n2) {
  return Number(n2 ?? 0).toLocaleString("en-IN", { maximumFractionDigits: 2 });
}
function DealsCard({ data }) {
  const raw = data?.data ?? data ?? [];
  const deals = Array.isArray(raw) ? raw : raw.deals ?? [];
  if (!deals.length) {
    return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-widest font-ui mb-2", children: "Bulk / Block Deals" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-sm font-ui", children: "No deals found." })
    ] });
  }
  const byDate = deals.reduce((acc, d) => {
    const key = d.date ?? "Today";
    (acc[key] = acc[key] ?? []).push(d);
    return acc;
  }, {});
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full space-y-4", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-muted text-[10px] uppercase tracking-widest font-ui", children: [
      "Bulk / Block Deals ",
      /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-subtle", children: [
        "(",
        deals.length,
        ")"
      ] })
    ] }),
    Object.entries(byDate).map(([date, group]) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-subtle text-[10px] font-ui mb-2", children: date }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("table", { className: "w-full text-[11px] font-mono", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("thead", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "text-muted text-[10px] uppercase tracking-wider border-b border-border", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left pb-2", children: "Symbol" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left pb-2", children: "Client" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left pb-2", children: "Entity" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-center pb-2", children: "Type" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-right pb-2", children: "Qty" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-right pb-2", children: "Price" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-right pb-2", children: "Class" })
        ] }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { children: group.map((d, i) => {
          const isBuy = d.deal_type?.toUpperCase() === "BUY";
          const entityCls = ENTITY_COLOR[d.entity_type] ?? ENTITY_COLOR.OTHER;
          return /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "border-b border-border/40 last:border-0", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "py-1.5 text-text font-semibold", children: d.symbol ?? "—" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "py-1.5 text-muted max-w-[120px] truncate", title: d.client, children: d.client ?? "—" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: `py-1.5 ${entityCls} text-[10px]`, children: d.entity_type ?? "—" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: `py-1.5 text-center font-semibold text-[10px] ${isBuy ? "text-green" : "text-red"}`, children: d.deal_type ?? "—" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "py-1.5 text-right text-text", children: fmt$2(d.quantity) }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs("td", { className: "py-1.5 text-right text-text", children: [
              "₹",
              fmt$2(d.price)
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "py-1.5 text-right text-subtle text-[10px]", children: d.deal_class ?? "—" })
          ] }, i);
        }) })
      ] })
    ] }, date))
  ] });
}
const IV_FLOOR = 0.5;
function IVSmileCard({ data }) {
  const d = data?.data ?? data ?? {};
  const symbol = d.symbol ?? "—";
  const expiry = d.expiry ?? "";
  const rows = (d.rows ?? []).slice().sort((a, b) => a.strike - b.strike);
  const setDraft = useChatStore((s) => s.setDraft);
  function ivValid(v2) {
    return Number(v2 ?? 0) >= IV_FLOOR;
  }
  function ivColor(iv) {
    const v2 = Number(iv ?? 0);
    if (v2 > 50) return "text-red";
    if (v2 > 30) return "text-amber";
    return "text-text";
  }
  function fmtIV(v2) {
    if (!ivValid(v2)) return "—";
    return Number(v2).toFixed(1) + "%";
  }
  let atmIdx = -1;
  if (rows.length > 0) {
    let minAbs = Infinity;
    rows.forEach((r2, i) => {
      const m2 = Math.abs(Number(r2.moneyness ?? 0));
      if (m2 < minAbs) {
        minAbs = m2;
        atmIdx = i;
      }
    });
  }
  const atmRow = atmIdx >= 0 ? rows[atmIdx] : null;
  const atmPeIv = atmRow ? Number(atmRow.pe_iv ?? 0) : 0;
  const atmStrike = atmRow ? Number(atmRow.strike) : 0;
  const belowAtm = rows.filter((_, i) => i < atmIdx && ivValid(Number(_.pe_iv ?? 0)));
  const maxSkewRow = belowAtm.length > 0 ? belowAtm.reduce((m2, r2) => Number(r2.pe_iv) > Number(m2.pe_iv) ? r2 : m2) : null;
  const aboveAtm = rows.filter((_, i) => i > atmIdx && ivValid(Number(_.ce_iv ?? 0)));
  const maxCeRow = aboveAtm.length > 0 ? aboveAtm.reduce((m2, r2) => Number(r2.ce_iv) > Number(m2.ce_iv) ? r2 : m2) : null;
  const ctx = [
    `${symbol} IV Smile`,
    atmStrike ? `ATM ${atmStrike.toLocaleString("en-IN")} PE IV=${atmPeIv.toFixed(1)}%` : "",
    maxSkewRow ? `max put skew at ${Number(maxSkewRow.strike).toLocaleString("en-IN")} = ${Number(maxSkewRow.pe_iv).toFixed(1)}%` : "",
    maxCeRow ? `max CE IV at ${Number(maxCeRow.strike).toLocaleString("en-IN")} = ${Number(maxCeRow.ce_iv).toFixed(1)}%` : ""
  ].filter(Boolean).join(", ");
  const chips = [
    maxSkewRow && {
      label: `Put skew +${Number(maxSkewRow.pe_iv).toFixed(0)}% at ${Number(maxSkewRow.strike).toLocaleString("en-IN")} — why?`,
      q: `${ctx}. Why is put IV so elevated vs call IV, and what does this skew structure tell me about market positioning for ${symbol}?`
    },
    atmPeIv > 0 && {
      label: `ATM IV ${atmPeIv.toFixed(1)}% — buy or sell options?`,
      q: `${ctx}. ATM IV is ${atmPeIv.toFixed(1)}%. Is this a good time to buy or sell ${symbol} options, and what strategies suit this IV level?`
    },
    {
      label: "How to trade this skew?",
      q: `${ctx}. What options strategies make the most sense given this skew structure — spreads, straddles, or directional plays?`
    }
  ].filter(Boolean);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full space-y-3", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-widest font-ui", children: "IV Smile" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-text text-lg font-mono font-semibold mt-0.5", children: symbol })
      ] }),
      expiry && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-muted text-[11px] font-ui border border-border px-2 py-0.5 rounded", children: expiry })
    ] }),
    rows.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[12px] font-ui text-center py-4", children: "No data available" }) : /* @__PURE__ */ jsxRuntimeExports.jsxs("table", { className: "w-full text-[11px] font-mono", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("thead", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "text-muted uppercase tracking-wider border-b border-border", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-right pb-2 pr-3", children: "Strike" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-right pb-2 pr-3", children: "CE IV%" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-right pb-2 pr-3", children: "PE IV%" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-right pb-2", children: "Skew (PE−CE)" })
      ] }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { children: rows.map((row, i) => {
        const ceIv = Number(row.ce_iv ?? 0);
        const peIv = Number(row.pe_iv ?? 0);
        const ceOk = ivValid(ceIv);
        const peOk = ivValid(peIv);
        const skew = ceOk && peOk ? peIv - ceIv : null;
        const isAtm = i === atmIdx;
        return /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "tr",
          {
            className: `border-b border-border/40 last:border-0 ${isAtm ? "bg-amber/5" : ""}`,
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsxs("td", { className: `py-1.5 text-right pr-3 font-semibold ${isAtm ? "text-amber" : "text-text"}`, children: [
                Number(row.strike).toLocaleString("en-IN"),
                isAtm && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-amber text-[9px] ml-1", children: "ATM" })
              ] }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: `py-1.5 text-right pr-3 ${ceOk ? ivColor(ceIv) : "text-muted"}`, children: fmtIV(ceIv) }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: `py-1.5 text-right pr-3 ${peOk ? ivColor(peIv) : "text-muted"}`, children: fmtIV(peIv) }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: `py-1.5 text-right ${skew == null ? "text-muted" : skew > 0 ? "text-green" : skew < 0 ? "text-red" : "text-muted"}`, children: skew == null ? "—" : `${skew >= 0 ? "+" : ""}${skew.toFixed(1)}%` })
            ]
          },
          i
        );
      }) })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex flex-wrap gap-2 pt-1", children: chips.map((chip) => /* @__PURE__ */ jsxRuntimeExports.jsx(
      "button",
      {
        onClick: () => setDraft(chip.q),
        className: "text-[11px] font-ui px-3 py-1.5 rounded-full border border-border\n                       text-muted hover:text-text hover:border-blue/50 hover:bg-blue/5\n                       transition-colors cursor-pointer",
        children: chip.label
      },
      chip.label
    )) })
  ] });
}
function GEXCard({ data }) {
  const setDraft = useChatStore((s) => s.setDraft);
  const d = data?.data ?? data ?? {};
  if (d.error) {
    return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-widest font-ui mb-2", children: "Gamma Exposure" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-red text-[12px] font-ui", children: d.error })
    ] });
  }
  const regime = (d.regime ?? "NEUTRAL").toUpperCase();
  const totalGex = Number(d.total_net_gex ?? 0);
  const flipPoint = d.flip_point ?? null;
  const regimeColor = regime === "POSITIVE" ? "text-green border-green/30" : regime === "NEGATIVE" ? "text-red border-red/30" : "text-amber border-amber/30";
  const regimeMsg = regime === "POSITIVE" ? "Dealers long gamma — market may pin/revert" : regime === "NEGATIVE" ? "Dealers short gamma — expect breakout/amplified moves" : "Balanced gamma exposure";
  const strikes = (d.strikes ?? []).slice().sort((a, b) => Math.abs(Number(b.net_gex ?? 0)) - Math.abs(Number(a.net_gex ?? 0))).slice(0, 10).sort((a, b) => Number(a.strike) - Number(b.strike));
  function fmtCr(v2) {
    const n2 = Number(v2 ?? 0);
    return (n2 / 1e7).toFixed(2) + "cr";
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full space-y-3", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-widest font-ui", children: "Gamma Exposure" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `text-[11px] font-ui border px-2 py-0.5 rounded font-semibold ${regimeColor}`, children: regime }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-text text-[12px] font-mono", children: [
          "GEX: ",
          fmtCr(totalGex)
        ] })
      ] })
    ] }),
    flipPoint != null && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "border border-border rounded-lg px-3 py-2", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-muted text-[10px] font-ui uppercase tracking-wider", children: "GEX Flip Point: " }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-blue text-[13px] font-mono font-semibold", children: [
        "₹",
        Number(flipPoint).toLocaleString("en-IN")
      ] })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[11px] font-ui italic", children: regimeMsg }),
    (() => {
      const flipFmt = flipPoint != null ? `₹${Number(flipPoint).toLocaleString("en-IN")}` : null;
      const gexFmt = `${(Math.abs(totalGex) / 1e7).toFixed(0)} Cr ${totalGex < 0 ? "short" : "long"} gamma`;
      const ctx = `NIFTY GEX: ${regime} regime, flip point ${flipFmt ?? "unknown"}, total ${gexFmt}`;
      const chips = [
        flipFmt && {
          label: `Flip at ${flipFmt} — what happens there?`,
          q: `${ctx}. What happens when NIFTY approaches the GEX flip point at ${flipFmt}, and should I position for a breakout or reversal?`
        },
        {
          label: regime === "NEGATIVE" ? "Moves amplified — how to trade it?" : regime === "POSITIVE" ? "Market pinning — how to trade it?" : "Balanced GEX — what does this mean?",
          q: `${ctx}. How should I trade a ${regime.toLowerCase()} gamma regime — which strategies benefit and which to avoid?`
        },
        {
          label: `${gexFmt} — how bearish/bullish is this?`,
          q: `${ctx}. How significant is ${gexFmt} and what does it imply for near-term ${regime === "NEGATIVE" ? "downside risk" : "market stability"}?`
        }
      ].filter(Boolean);
      return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex flex-wrap gap-2", children: chips.map((chip) => /* @__PURE__ */ jsxRuntimeExports.jsx(
        "button",
        {
          onClick: () => setDraft(chip.q),
          className: "text-[11px] font-ui px-3 py-1.5 rounded-full border border-border\n                           text-muted hover:text-text hover:border-blue/50 hover:bg-blue/5\n                           transition-colors cursor-pointer",
          children: chip.label
        },
        chip.label
      )) });
    })(),
    strikes.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("table", { className: "w-full text-[11px] font-mono", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("thead", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "text-muted uppercase tracking-wider border-b border-border", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-right pb-2 pr-3", children: "Strike" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-right pb-2 pr-3", children: "CE GEX" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-right pb-2 pr-3", children: "PE GEX" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-right pb-2", children: "Net" })
      ] }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { children: strikes.map((row, i) => {
        const net = Number(row.net_gex ?? 0);
        return /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "border-b border-border/40 last:border-0", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "py-1.5 text-right pr-3 text-text font-semibold", children: Number(row.strike).toLocaleString("en-IN") }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "py-1.5 text-right pr-3 text-muted", children: fmtCr(row.ce_gex) }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "py-1.5 text-right pr-3 text-muted", children: fmtCr(row.pe_gex) }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("td", { className: `py-1.5 text-right font-semibold ${net > 0 ? "text-green" : net < 0 ? "text-red" : "text-muted"}`, children: [
            net >= 0 ? "+" : "",
            fmtCr(net)
          ] })
        ] }, i);
      }) })
    ] })
  ] });
}
function deltaColor(v2) {
  const n2 = Number(v2 ?? 0);
  if (Math.abs(n2) < 0.01) return "text-muted";
  return n2 > 0 ? "text-green" : "text-red";
}
function DeltaHedgeCard({ data }) {
  const d = data?.data ?? data ?? {};
  const demo = d.demo ?? false;
  const suggestions = d.suggestions ?? [];
  const currentDelta = Number(d.current_delta ?? 0);
  const targetDelta = Number(d.target_delta ?? 0);
  const gap = Number(d.gap ?? 0);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full space-y-3", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-widest font-ui", children: "Delta Hedge" }),
      demo && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-amber text-[10px] font-ui border border-amber/30 px-1.5 py-0.5 rounded", children: "demo" })
    ] }),
    demo && d.message && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "border border-amber/30 bg-amber/5 rounded-lg px-3 py-2", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-amber text-[11px] font-ui", children: [
      "⚠ ",
      d.message
    ] }) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid grid-cols-3 gap-2", children: [
      { label: "Current Δ", value: currentDelta },
      { label: "Target Δ", value: targetDelta },
      { label: "Gap", value: gap }
    ].map(({ label, value }) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-panel border border-border rounded-lg p-3", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-wider font-ui", children: label }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: `text-[15px] font-mono font-semibold mt-1 ${deltaColor(value)}`, children: [
        value >= 0 ? "+" : "",
        value.toFixed(2)
      ] })
    ] }, label)) }),
    suggestions.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-wider font-ui mb-2", children: "Hedge Suggestions" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("table", { className: "w-full text-[11px] font-mono", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("thead", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "text-muted uppercase tracking-wider border-b border-border", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left pb-2", children: "Action" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left pb-2", children: "Instrument" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-right pb-2", children: "Lots" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-right pb-2", children: "Δ Change" })
        ] }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { children: suggestions.map((s, i) => {
          const action = (s.action ?? "").toUpperCase();
          const isBuy = action === "BUY";
          return /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "border-b border-border/40 last:border-0", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: `py-1.5 font-semibold ${isBuy ? "text-green" : "text-red"}`, children: action }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "py-1.5 text-text", children: s.instrument ?? "—" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "py-1.5 text-right text-text", children: s.lots ?? "—" }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs("td", { className: `py-1.5 text-right ${deltaColor(s.delta_change)}`, children: [
              Number(s.delta_change ?? 0) >= 0 ? "+" : "",
              Number(s.delta_change ?? 0).toFixed(2)
            ] })
          ] }, i);
        }) })
      ] })
    ] }),
    d.cost_estimate != null && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "border-t border-border pt-2 flex items-center justify-between", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[11px] font-ui", children: "Estimated Cost" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-text text-[12px] font-mono font-semibold", children: [
        "₹",
        Number(d.cost_estimate).toLocaleString("en-IN")
      ] })
    ] })
  ] });
}
function fmt$1(n2) {
  return Number(n2 ?? 0).toLocaleString("en-IN");
}
function concColor(risk) {
  const r2 = (risk ?? "").toUpperCase();
  if (r2 === "LOW") return "text-green border-green/30";
  if (r2 === "HIGH") return "text-red border-red/30";
  return "text-amber border-amber/30";
}
function RiskReportCard({ data }) {
  const d = data?.data ?? data ?? {};
  const demo = d.demo ?? false;
  const portfolioValue = Number(d.portfolio_value ?? 0);
  const holdings = (d.holding_vars ?? []).slice().sort((a, b) => Math.abs(Number(b.var_95 ?? 0)) - Math.abs(Number(a.var_95 ?? 0)));
  const highCorr = d.high_correlations ?? [];
  const concRisk = d.concentration_risk ?? "MEDIUM";
  const tiles = [
    { label: "Portfolio Value", value: `₹${fmt$1(d.portfolio_value)}` },
    { label: "1-day VaR 95%", value: `₹${fmt$1(d.portfolio_var_95)}`, sub: "at 95% confidence" },
    { label: "VaR 99%", value: `₹${fmt$1(d.portfolio_var_99)}`, sub: "at 99% confidence" },
    { label: "Volatility", value: `${Number(d.portfolio_volatility ?? 0).toFixed(1)}%`, sub: "annualised" }
  ];
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full space-y-3", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-widest font-ui", children: "Risk Report" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
        demo && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-amber text-[10px] font-ui border border-amber/30 px-1.5 py-0.5 rounded", children: "demo" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: `text-[11px] font-ui border px-2 py-0.5 rounded font-semibold ${concColor(concRisk)}`, children: [
          concRisk,
          " CONCENTRATION"
        ] })
      ] })
    ] }),
    demo && d.message && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "border border-amber/30 bg-amber/5 rounded-lg px-3 py-2", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-amber text-[11px] font-ui", children: [
      "⚠ ",
      d.message
    ] }) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid grid-cols-2 gap-2", children: tiles.map((t2) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-panel border border-border rounded-lg p-3", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-wider font-ui", children: t2.label }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-text text-[15px] font-mono font-semibold mt-1", children: t2.value }),
      t2.sub && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] font-ui mt-0.5", children: t2.sub })
    ] }, t2.label)) }),
    holdings.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-wider font-ui mb-2", children: "Top Holdings by VaR" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("table", { className: "w-full text-[11px] font-mono", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("thead", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "text-muted uppercase tracking-wider border-b border-border", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left pb-2", children: "Symbol" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-right pb-2", children: "Weight%" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-right pb-2", children: "1-day VaR" })
        ] }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { children: holdings.slice(0, 8).map((h, i) => /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "border-b border-border/40 last:border-0", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "py-1.5 text-text", children: h.symbol ?? "—" }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("td", { className: "py-1.5 text-right text-muted", children: [
            portfolioValue > 0 ? (Number(h.position_value ?? 0) / portfolioValue * 100).toFixed(1) : "0.0",
            "%"
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("td", { className: "py-1.5 text-right text-red", children: [
            "₹",
            fmt$1(h.var_95)
          ] })
        ] }, i)) })
      ] })
    ] }),
    highCorr.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "border-t border-border pt-2 space-y-1", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-wider font-ui mb-1", children: "Correlation Warnings" }),
      highCorr.map((c, i) => /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-amber text-[11px] font-ui flex gap-1.5", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: "⚠" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: typeof c === "string" ? c : JSON.stringify(c) })
      ] }, i))
    ] })
  ] });
}
function retColor(v2) {
  const n2 = Number(v2 ?? 0);
  return n2 > 0 ? "text-green" : n2 < 0 ? "text-red" : "text-muted";
}
function WalkForwardCard({ data }) {
  const d = data?.data ?? data ?? {};
  const symbol = d.symbol ?? "—";
  const strategy = d.strategy ?? d.strategy_name ?? "—";
  const windows = d.windows ?? [];
  const avgReturn = Number(d.avg_return ?? d.average_return ?? 0);
  const avgSharpe = Number(d.avg_sharpe ?? d.average_sharpe ?? 0);
  const avgWinRate = Number(d.avg_win_rate ?? d.average_win_rate ?? 0);
  const consistency = d.consistency ?? null;
  const summaryStats = [
    { label: "Avg Return", value: `${avgReturn >= 0 ? "+" : ""}${avgReturn.toFixed(2)}%`, color: retColor(avgReturn) },
    { label: "Avg Sharpe", value: avgSharpe.toFixed(2), color: avgSharpe >= 1 ? "text-green" : avgSharpe >= 0 ? "text-amber" : "text-red" },
    { label: "Avg Win Rate", value: `${(avgWinRate * 100).toFixed(1)}%`, color: avgWinRate >= 0.55 ? "text-green" : avgWinRate >= 0.45 ? "text-amber" : "text-red" },
    { label: "Windows", value: String(windows.length), color: "text-text" }
  ];
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full space-y-3", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-widest font-ui", children: "Walk-Forward Backtest" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-text text-[14px] font-mono font-semibold mt-0.5", children: [
        symbol,
        " ",
        /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-muted font-normal", children: [
          "(",
          strategy,
          ")"
        ] })
      ] })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid grid-cols-4 gap-2", children: summaryStats.map((s) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-panel border border-border rounded-lg p-2.5", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-wider font-ui", children: s.label }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: `text-[14px] font-mono font-semibold mt-1 ${s.color}`, children: s.value })
    ] }, s.label)) }),
    windows.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("table", { className: "w-full text-[11px] font-mono", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("thead", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "text-muted uppercase tracking-wider border-b border-border", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left pb-2", children: "Period" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-right pb-2", children: "Return%" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-right pb-2", children: "Sharpe" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-right pb-2", children: "Win Rate" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-right pb-2", children: "Trades" })
      ] }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { children: windows.map((w2, i) => {
        const ret = Number(w2.return_pct ?? w2.return ?? 0);
        const sharpe = Number(w2.sharpe ?? w2.sharpe_ratio ?? 0);
        const winRate = Number(w2.win_rate ?? 0);
        return /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "border-b border-border/40 last:border-0", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "py-1.5 text-text", children: w2.period ?? w2.window ?? `W${i + 1}` }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("td", { className: `py-1.5 text-right ${retColor(ret)}`, children: [
            ret >= 0 ? "+" : "",
            ret.toFixed(2),
            "%"
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: `py-1.5 text-right ${sharpe >= 1 ? "text-green" : sharpe >= 0 ? "text-amber" : "text-red"}`, children: sharpe.toFixed(2) }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("td", { className: "py-1.5 text-right text-text", children: [
            (winRate * 100).toFixed(1),
            "%"
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "py-1.5 text-right text-muted", children: w2.trades ?? "—" })
        ] }, i);
      }) })
    ] }),
    consistency != null && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "border-t border-border pt-2", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-muted text-[11px] font-ui", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-muted", children: "Consistency: " }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-text font-mono", children: typeof consistency === "number" ? `${(consistency * 100).toFixed(1)}%` : String(consistency) })
    ] }) })
  ] });
}
function pnlColor(v2) {
  const n2 = Number(v2 ?? 0);
  return n2 > 0 ? "text-green" : n2 < 0 ? "text-red" : "text-muted";
}
function fmt(n2) {
  return Number(n2 ?? 0).toLocaleString("en-IN");
}
function ScenarioMini({ sc: sc2 }) {
  const pnl = Number(sc2.projected_pnl ?? 0);
  const pct2 = Number(sc2.projected_pnl_pct ?? 0);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-panel border border-border rounded-lg p-3 flex-1 min-w-0", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] font-ui uppercase tracking-wider truncate", children: sc2.scenario_name ?? "Scenario" }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: `text-[15px] font-mono font-semibold mt-1 ${pnlColor(pnl)}`, children: [
      pnl >= 0 ? "+" : "",
      "₹",
      fmt(pnl)
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: `text-[11px] font-mono ${pnlColor(pct2)}`, children: [
      pct2 >= 0 ? "+" : "",
      pct2.toFixed(2),
      "%"
    ] })
  ] });
}
function WhatIfCard({ data }) {
  const d = data?.data ?? data ?? {};
  const demo = d.demo ?? false;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full space-y-3", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-widest font-ui", children: "What-If Analysis" }),
      demo && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-amber text-[10px] font-ui border border-amber/30 px-1.5 py-0.5 rounded", children: "demo" })
    ] }),
    demo && d.message && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "border border-amber/30 bg-amber/5 rounded-lg px-3 py-2", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-amber text-[11px] font-ui", children: [
      "⚠ ",
      d.message
    ] }) }),
    d.multi && d.scenarios?.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex gap-2 flex-wrap", children: d.scenarios.map((sc2, i) => /* @__PURE__ */ jsxRuntimeExports.jsx(ScenarioMini, { sc: sc2 }, i)) }),
    !d.multi && /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
      d.scenario_name && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-text text-[13px] font-semibold font-ui", children: d.scenario_name }),
        d.description && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[11px] font-ui mt-0.5", children: d.description })
      ] }),
      (d.current_value != null || d.projected_value != null) && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-3 gap-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-panel border border-border rounded-lg p-3", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-wider font-ui", children: "Current" }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-text text-[14px] font-mono font-semibold mt-1", children: [
            "₹",
            fmt(d.current_value)
          ] })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-panel border border-border rounded-lg p-3", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-wider font-ui", children: "Projected" }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-text text-[14px] font-mono font-semibold mt-1", children: [
            "₹",
            fmt(d.projected_value)
          ] })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-panel border border-border rounded-lg p-3", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-wider font-ui", children: "P&L" }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: `text-[14px] font-mono font-semibold mt-1 ${pnlColor(d.projected_pnl)}`, children: [
            Number(d.projected_pnl ?? 0) >= 0 ? "+" : "",
            "₹",
            fmt(d.projected_pnl)
          ] }),
          d.projected_pnl_pct != null && /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: `text-[10px] font-mono ${pnlColor(d.projected_pnl_pct)}`, children: [
            Number(d.projected_pnl_pct ?? 0) >= 0 ? "+" : "",
            Number(d.projected_pnl_pct ?? 0).toFixed(2),
            "%"
          ] })
        ] })
      ] }),
      d.impacts?.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-wider font-ui mb-2", children: "Position Impacts" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("table", { className: "w-full text-[11px] font-mono", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("thead", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "text-muted uppercase tracking-wider border-b border-border", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left pb-2", children: "Symbol" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-right pb-2", children: "Current" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-right pb-2", children: "Projected" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-right pb-2", children: "Δ%" })
          ] }) }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { children: d.impacts.map((imp, i) => {
            const chg = Number(imp.change_pct ?? 0);
            return /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "border-b border-border/40 last:border-0", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "py-1.5 text-text", children: imp.symbol ?? "—" }),
              /* @__PURE__ */ jsxRuntimeExports.jsxs("td", { className: "py-1.5 text-right text-muted", children: [
                "₹",
                fmt(imp.current_value)
              ] }),
              /* @__PURE__ */ jsxRuntimeExports.jsxs("td", { className: "py-1.5 text-right text-text", children: [
                "₹",
                fmt(imp.projected_value)
              ] }),
              /* @__PURE__ */ jsxRuntimeExports.jsxs("td", { className: `py-1.5 text-right font-semibold ${pnlColor(chg)}`, children: [
                chg >= 0 ? "+" : "",
                chg.toFixed(2),
                "%"
              ] })
            ] }, i);
          }) })
        ] })
      ] })
    ] })
  ] });
}
function fitBadge(score) {
  const s = Number(score ?? 0);
  if (s >= 80) return "text-green border-green/30";
  if (s >= 60) return "text-amber border-amber/30";
  return "text-muted border-border";
}
function StrategyBlock({ strat, isTop }) {
  const [expanded, setExpanded] = reactExports.useState(false);
  const legs = strat.legs ?? [];
  const breakeven = strat.breakeven ?? [];
  const fitScore = Number(strat.fit_score ?? 0);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: `border rounded-lg p-3 space-y-2 ${isTop ? "border-amber/40 bg-amber/5" : "border-border"}`, children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between gap-2", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 min-w-0", children: [
        isTop && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-amber text-[11px]", children: "⭐ Top Pick" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-text text-[13px] font-semibold font-ui truncate", children: strat.name ?? "—" })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: `text-[10px] font-ui border px-1.5 py-0.5 rounded shrink-0 ${fitBadge(fitScore)}`, children: [
        "Fit ",
        fitScore
      ] })
    ] }),
    strat.description && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[11px] font-ui", children: strat.description }),
    legs.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex flex-wrap gap-1.5", children: legs.map((leg, i) => {
      const action = (leg.action ?? "").toUpperCase();
      return /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "span",
        {
          className: `text-[10px] font-mono border rounded px-1.5 py-0.5 ${action === "BUY" ? "text-green border-green/30 bg-green/5" : action === "SELL" ? "text-red border-red/30 bg-red/5" : "text-muted border-border"}`,
          children: [
            action,
            " ",
            leg.strike ? Number(leg.strike).toLocaleString("en-IN") : "",
            " ",
            leg.type ?? "",
            leg.lots ? ` ×${leg.lots}` : ""
          ]
        },
        i
      );
    }) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid grid-cols-4 gap-1.5 text-[10px] font-mono", children: [
      { label: "Capital", value: strat.capital_needed != null ? `₹${Number(strat.capital_needed).toLocaleString("en-IN")}` : "—" },
      { label: "Max Profit", value: strat.max_profit != null ? strat.max_profit === Infinity || strat.max_profit === "unlimited" ? "∞" : `₹${Number(strat.max_profit).toLocaleString("en-IN")}` : "—", green: true },
      { label: "Max Loss", value: strat.max_loss != null ? `₹${Number(strat.max_loss).toLocaleString("en-IN")}` : "—", red: true },
      { label: "R:R", value: strat.rr_ratio != null ? `${Number(strat.rr_ratio).toFixed(1)}x` : "—" }
    ].map((m2) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-panel border border-border rounded p-1.5", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[9px] uppercase tracking-wider", children: m2.label }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: `font-semibold mt-0.5 ${m2.green ? "text-green" : m2.red ? "text-red" : "text-text"}`, children: m2.value })
    ] }, m2.label)) }),
    breakeven.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-muted text-[10px] font-mono", children: [
      "BE: ",
      breakeven.map((b) => `₹${Number(b).toLocaleString("en-IN")}`).join(" / ")
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      "button",
      {
        onClick: () => setExpanded((e) => !e),
        className: "text-blue text-[10px] font-ui hover:underline",
        children: expanded ? "▲ Hide details" : "▼ Best for & risks"
      }
    ),
    expanded && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-1.5 pt-1 border-t border-border", children: [
      strat.best_for && /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-green text-[11px] font-ui", children: [
        "✓ ",
        strat.best_for
      ] }),
      strat.risks && /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-red text-[11px] font-ui", children: [
        "⚠ ",
        strat.risks
      ] })
    ] })
  ] });
}
function StrategyCard({ data }) {
  const d = data?.data ?? data ?? {};
  const symbol = d.symbol ?? "—";
  const view = d.view ?? "—";
  const dte = d.dte ?? "—";
  const topName = d.top?.name ?? null;
  const strategies = (d.strategies ?? []).slice(0, 3);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full space-y-3", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-widest font-ui", children: "Strategy Recommendations" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-text text-[14px] font-mono font-semibold mt-0.5", children: [
        symbol,
        /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-muted font-normal text-[12px]", children: [
          " | ",
          view,
          " | ",
          dte,
          " days"
        ] })
      ] })
    ] }),
    strategies.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[12px] font-ui text-center py-4", children: "No strategies available" }) : /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "space-y-2", children: strategies.map((strat, i) => /* @__PURE__ */ jsxRuntimeExports.jsx(StrategyBlock, { strat, isTop: topName != null && strat.name === topName }, i)) })
  ] });
}
function trendBadge(trend) {
  const t2 = (trend ?? "").toUpperCase();
  if (t2 === "IMPROVING") return { text: "IMPROVING", cls: "text-green border-green/30" };
  if (t2 === "DECLINING") return { text: "DECLINING", cls: "text-red border-red/30" };
  return { text: "STABLE", cls: "text-amber border-amber/30" };
}
function pct(v2, decimals = 1) {
  return (Number(v2 ?? 0) * 100).toFixed(decimals) + "%";
}
function DriftCard({ data }) {
  const d = data?.data ?? data ?? {};
  const trend = trendBadge(d.win_rate_trend);
  const analystAcc = d.analyst_accuracy ?? {};
  const alerts = d.alerts ?? [];
  const recentWr = Number(d.recent_win_rate ?? 0);
  const olderWr = Number(d.older_win_rate ?? 0);
  const delta = Number(d.win_rate_delta ?? recentWr - olderWr);
  const dirTiles = [
    { label: "BUY", value: d.buy_accuracy != null ? pct(d.buy_accuracy) : "—", color: "text-green" },
    { label: "SELL", value: d.sell_accuracy != null ? pct(d.sell_accuracy) : "—", color: "text-red" },
    { label: "HOLD", value: d.hold_accuracy != null ? pct(d.hold_accuracy) : "—", color: "text-muted" }
  ];
  const analystRows = Object.entries(analystAcc).map(([name, acc]) => ({ name, acc: Number(acc) })).sort((a, b) => b.acc - a.acc);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full space-y-3", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-widest font-ui", children: "Model Accuracy Drift" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `text-[11px] font-ui border px-2 py-0.5 rounded font-semibold ${trend.cls}`, children: trend.text })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-3 gap-2", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-panel border border-border rounded-lg p-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-wider font-ui", children: "Recent Win Rate" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-text text-[15px] font-mono font-semibold mt-1", children: pct(recentWr) })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-panel border border-border rounded-lg p-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-wider font-ui", children: "Older Win Rate" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-text text-[15px] font-mono font-semibold mt-1", children: pct(olderWr) })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-panel border border-border rounded-lg p-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-wider font-ui", children: "Δ Change" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: `text-[15px] font-mono font-semibold mt-1 ${delta > 0 ? "text-green" : delta < 0 ? "text-red" : "text-muted"}`, children: [
          delta >= 0 ? "+" : "",
          (delta * 100).toFixed(1),
          "pp"
        ] })
      ] })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-wider font-ui mb-2", children: "Direction Accuracy" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex gap-2", children: dirTiles.map((t2) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-panel border border-border rounded-lg p-2.5 flex-1 text-center", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] font-ui uppercase", children: t2.label }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: `text-[15px] font-mono font-semibold mt-1 ${t2.color}`, children: t2.value })
      ] }, t2.label)) })
    ] }),
    analystRows.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-wider font-ui mb-2", children: "Analyst Accuracy" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("table", { className: "w-full text-[11px] font-mono", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("thead", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "text-muted uppercase tracking-wider border-b border-border", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left pb-2", children: "Analyst" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-right pb-2", children: "Accuracy" })
        ] }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { children: analystRows.map((row, i) => /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "border-b border-border/40 last:border-0", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "py-1.5 text-text", children: row.name }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("td", { className: `py-1.5 text-right font-semibold ${row.acc >= 0.6 ? "text-green" : row.acc >= 0.45 ? "text-amber" : "text-red"}`, children: [
            (row.acc * 100).toFixed(1),
            "%"
          ] })
        ] }, i)) })
      ] })
    ] }),
    alerts.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "border-t border-border pt-2 space-y-1", children: alerts.map((a, i) => /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-amber text-[11px] font-ui flex gap-1.5", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: "⚠" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: typeof a === "string" ? a : JSON.stringify(a) })
    ] }, i)) })
  ] });
}
function signalBadge(signal) {
  const s = (signal ?? "").toUpperCase();
  if (s.includes("BUY")) return { text: s, cls: "text-green border-green/30" };
  if (s.includes("SELL")) return { text: s, cls: "text-red border-red/30" };
  return { text: s || "NEUTRAL", cls: "text-muted border-border" };
}
function corrColor(v2) {
  const n2 = Math.abs(Number(v2 ?? 0));
  if (n2 >= 0.8) return "text-green";
  if (n2 >= 0.5) return "text-amber";
  return "text-red";
}
function PairsCard({ data }) {
  const d = data?.data ?? data ?? {};
  const stockA = d.stock_a ?? d.symbol_a ?? "—";
  const stockB = d.stock_b ?? d.symbol_b ?? "—";
  const correlation = Number(d.correlation ?? 0);
  const zScore = Number(d.z_score ?? 0);
  const spreadMean = Number(d.spread_mean ?? 0);
  const spreadStd = Number(d.spread_std ?? 0);
  const cointegrated = d.cointegrated ?? null;
  const sig = signalBadge(d.signal);
  const metrics = [
    { label: "Correlation", value: correlation.toFixed(3), color: corrColor(correlation) },
    { label: "Z-Score", value: zScore.toFixed(2), color: Math.abs(zScore) > 2 ? "text-amber" : Math.abs(zScore) > 3 ? "text-red" : "text-text" },
    { label: "Spread Mean", value: spreadMean.toFixed(4), color: "text-text" },
    { label: "Spread Std", value: spreadStd.toFixed(4), color: "text-text" }
  ];
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full space-y-3", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-widest font-ui", children: "Pairs Analysis" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-text text-lg font-mono font-semibold mt-0.5", children: [
          stockA,
          " ",
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-muted", children: "vs" }),
          " ",
          stockB
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
        cointegrated != null && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `text-[10px] font-ui border px-1.5 py-0.5 rounded ${cointegrated ? "text-green border-green/30" : "text-muted border-border"}`, children: cointegrated ? "Cointegrated" : "Not Cointegrated" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `text-[11px] font-ui border px-2 py-0.5 rounded font-semibold ${sig.cls}`, children: sig.text })
      ] })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid grid-cols-4 gap-2", children: metrics.map((m2) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-panel border border-border rounded-lg p-2.5", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-wider font-ui", children: m2.label }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: `text-[14px] font-mono font-semibold mt-1 ${m2.color}`, children: m2.value })
    ] }, m2.label)) }),
    d.description && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "border border-border rounded-lg px-3 py-2", children: /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[11px] font-ui leading-relaxed", children: d.description }) })
  ] });
}
function verdictColor(v2) {
  const s = (v2 ?? "").toUpperCase();
  if (s === "BULLISH") return "text-green";
  if (s === "BEARISH") return "text-red";
  return "text-amber";
}
function outcomeColor(o) {
  const s = (o ?? "").toUpperCase();
  if (s === "WIN") return "text-green";
  if (s === "LOSS") return "text-red";
  if (s === "BREAKEVEN") return "text-muted";
  return "text-subtle";
}
function fmtDate(s) {
  if (!s) return "—";
  return new Date(s).toLocaleDateString("en-IN", { day: "2-digit", month: "short" });
}
function MemoryCard({ data }) {
  const d = data?.data ?? data ?? {};
  const stats = d.stats ?? {};
  const records = d.records ?? [];
  const winRate = Number(stats.win_rate ?? 0);
  const totalPnl = Number(stats.total_pnl ?? 0);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full space-y-4", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-widest font-ui", children: "Trade Memory" }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid grid-cols-4 gap-2", children: [
      { label: "Analyses", value: stats.total_analyses ?? 0 },
      { label: "Win Rate", value: `${winRate.toFixed(1)}%`, color: winRate >= 55 ? "text-green" : winRate < 40 ? "text-red" : "text-amber" },
      { label: "Total P&L", value: `${totalPnl >= 0 ? "+" : ""}₹${Math.abs(totalPnl).toLocaleString("en-IN")}`, color: totalPnl >= 0 ? "text-green" : "text-red" },
      { label: "Avg Conf", value: `${Number(stats.avg_confidence ?? 0).toFixed(0)}%` }
    ].map(({ label, value, color }) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-panel border border-border rounded-lg p-2 text-center", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[9px] uppercase tracking-wider font-ui", children: label }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: `text-[13px] font-mono font-semibold mt-0.5 ${color ?? "text-text"}`, children: value })
    ] }, label)) }),
    records.length > 0 ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "overflow-x-auto", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("table", { className: "w-full text-[11px]", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("thead", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "text-muted text-[9px] uppercase tracking-wider font-ui border-b border-border", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "pb-1 text-left pr-3", children: "Date" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "pb-1 text-left pr-3", children: "Symbol" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "pb-1 text-left pr-3", children: "Verdict" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "pb-1 text-right pr-3", children: "Conf" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "pb-1 text-left pr-3", children: "Outcome" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "pb-1 text-right", children: "P&L" })
        ] }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { children: records.slice(0, 12).map((r2, i) => {
          const pnl = r2.pnl != null ? Number(r2.pnl) : null;
          return /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "border-b border-border/50 hover:bg-panel/50", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "py-1 pr-3 font-mono text-muted", children: fmtDate(r2.created_at ?? r2.date) }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "py-1 pr-3 font-mono text-text font-semibold", children: r2.symbol ?? "—" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: `py-1 pr-3 font-ui ${verdictColor(r2.verdict)}`, children: r2.verdict ?? "—" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "py-1 pr-3 font-mono text-muted text-right", children: r2.confidence ? `${r2.confidence}%` : "—" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: `py-1 pr-3 font-ui ${outcomeColor(r2.outcome)}`, children: r2.outcome ?? "—" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: `py-1 font-mono text-right ${pnl == null ? "text-subtle" : pnl >= 0 ? "text-green" : "text-red"}`, children: pnl == null ? "—" : `${pnl >= 0 ? "+" : ""}₹${Math.abs(pnl).toLocaleString("en-IN")}` })
          ] }, i);
        }) })
      ] }),
      records.length > 12 && /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-subtle text-[10px] font-ui mt-1", children: [
        records.length - 12,
        " more — use memory query to filter"
      ] })
    ] }) : /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[12px] font-ui text-center py-4", children: "No trade records yet. Run analyze SYMBOL to start building memory." })
  ] });
}
function qualityColor(q2) {
  const s = (q2 ?? "").toUpperCase();
  if (s === "GOOD") return "text-green";
  if (s === "FAIR") return "text-amber";
  return "text-red";
}
function AuditCard({ data }) {
  const d = data?.data ?? data ?? {};
  const grades = d.analyst_grades ?? [];
  const lessons = d.lessons ?? [];
  const pnl = d.pnl != null ? Number(d.pnl) : null;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full space-y-4", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-widest font-ui", children: "Trade Audit" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-text text-lg font-mono font-semibold mt-0.5", children: d.symbol ?? "—" })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "text-right space-y-1", children: [
        d.outcome && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `text-[12px] font-ui font-semibold border rounded px-2 py-0.5 ${d.outcome === "WIN" ? "text-green border-green/30 bg-green/5" : d.outcome === "LOSS" ? "text-red border-red/30 bg-red/5" : "text-muted border-border"}`, children: d.outcome }),
        pnl != null && /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: `text-[12px] font-mono ${pnl >= 0 ? "text-green" : "text-red"}`, children: [
          pnl >= 0 ? "+" : "",
          "₹",
          Math.abs(pnl).toLocaleString("en-IN")
        ] })
      ] })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid grid-cols-3 gap-2", children: [
      { label: "Entry", value: d.entry_quality },
      { label: "Stop-Loss", value: d.sl_assessment },
      { label: "Hold", value: d.hold_assessment }
    ].map(({ label, value }) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-panel border border-border rounded-lg p-2 text-center", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[9px] uppercase tracking-wider font-ui", children: label }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: `text-[12px] font-ui font-semibold mt-0.5 ${qualityColor(value)}`, children: value ?? "—" })
    ] }, label)) }),
    grades.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-wider font-ui mb-2", children: "Analyst Grades" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("table", { className: "w-full text-[11px]", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("thead", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "text-muted text-[9px] font-ui border-b border-border", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "pb-1 text-left pr-3", children: "Analyst" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "pb-1 text-left pr-3", children: "Grade" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "pb-1 text-right", children: "Accuracy" })
        ] }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { children: grades.map((g, i) => /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "border-b border-border/50", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "py-1 pr-3 font-ui text-text", children: g.analyst ?? "—" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: `py-1 pr-3 font-mono font-semibold ${g.grade === "A" ? "text-green" : g.grade === "B" ? "text-blue" : g.grade === "C" ? "text-amber" : "text-red"}`, children: g.grade ?? "—" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "py-1 font-mono text-muted text-right", children: g.accuracy != null ? `${Number(g.accuracy).toFixed(0)}%` : "—" })
        ] }, i)) })
      ] })
    ] }),
    (d.most_accurate || d.most_wrong) && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex gap-3 text-[11px]", children: [
      d.most_accurate && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex-1 bg-green/5 border border-green/20 rounded-lg px-3 py-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[9px] uppercase font-ui", children: "Most Accurate" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-green font-ui font-semibold mt-0.5", children: d.most_accurate })
      ] }),
      d.most_wrong && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex-1 bg-red/5 border border-red/20 rounded-lg px-3 py-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[9px] uppercase font-ui", children: "Most Wrong" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-red font-ui font-semibold mt-0.5", children: d.most_wrong })
      ] })
    ] }),
    lessons.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-wider font-ui mb-2", children: "Lessons" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("ul", { className: "space-y-1", children: lessons.map((l2, i) => /* @__PURE__ */ jsxRuntimeExports.jsxs("li", { className: "flex gap-2 text-[11px] font-ui text-text", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-blue mt-0.5", children: "›" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: l2 })
      ] }, i)) })
    ] })
  ] });
}
function TelegramCard({ data }) {
  const d = data?.data ?? data ?? {};
  const configured = d.configured ?? false;
  const running = d.running ?? false;
  const hint = d.token_hint;
  const BOT_COMMANDS = [
    { cmd: "/quote INFY", desc: "Live price" },
    { cmd: "/analyze INFY", desc: "Full AI analysis" },
    { cmd: "/brief", desc: "Morning market brief" },
    { cmd: "/flows", desc: "FII/DII flows" },
    { cmd: "/alerts", desc: "List active alerts" },
    { cmd: "/macro", desc: "Macro snapshot" },
    { cmd: "/memory", desc: "Trade history" },
    { cmd: "/help", desc: "All commands" }
  ];
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full space-y-4", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-widest font-ui", children: "Telegram Bot" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `text-[10px] font-ui border rounded px-2 py-0.5 ${running ? "text-green border-green/30 bg-green/5" : configured ? "text-amber border-amber/30 bg-amber/5" : "text-red border-red/30 bg-red/5"}`, children: running ? "● Running" : configured ? "◌ Configured" : "○ Not configured" })
    ] }),
    !configured && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "border border-border bg-panel rounded-lg px-3 py-3 space-y-2", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[11px] font-ui", children: "To enable Telegram alerts and commands:" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("ol", { className: "space-y-1 text-[11px] font-ui text-text list-decimal list-inside", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("li", { children: [
          "Create a bot via ",
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-blue", children: "@BotFather" }),
          " on Telegram"
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("li", { children: "Copy the bot token" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("li", { children: [
          "In the CLI: ",
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "font-mono text-amber bg-panel px-1 rounded", children: "credentials setup" })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("li", { children: [
          "Enter the token as ",
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "font-mono text-amber", children: "TELEGRAM_BOT_TOKEN" })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("li", { children: [
          "Start the bot: ",
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "font-mono text-amber bg-panel px-1 rounded", children: "telegram start" })
        ] })
      ] })
    ] }),
    configured && !running && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "border border-amber/30 bg-amber/5 rounded-lg px-3 py-2", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-amber text-[11px] font-ui", children: [
      "Token configured ",
      hint ? `(…${hint})` : "",
      ". Start the bot from the CLI: ",
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "font-mono", children: "telegram start" })
    ] }) }),
    running && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "border border-green/30 bg-green/5 rounded-lg px-3 py-2", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-green text-[11px] font-ui", children: [
      "Bot is active ",
      hint ? `· token …${hint}` : ""
    ] }) }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-wider font-ui mb-2", children: "Bot Commands" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid grid-cols-2 gap-1.5", children: BOT_COMMANDS.map(({ cmd, desc }) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 bg-panel border border-border rounded px-2 py-1.5", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-blue text-[10px] font-mono", children: cmd }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-muted text-[10px] font-ui truncate", children: desc })
      ] }, cmd)) })
    ] })
  ] });
}
const PROVIDER_META = {
  anthropic: { label: "Anthropic", color: "text-blue", bg: "bg-blue/5   border-blue/20", dot: "#5294e0" },
  openai: { label: "OpenAI", color: "text-green", bg: "bg-green/5  border-green/20", dot: "#52e07a" },
  gemini: { label: "Google Gemini", color: "text-amber", bg: "bg-amber/5  border-amber/20", dot: "#e06c00" },
  ollama: { label: "Ollama (local)", color: "text-muted", bg: "bg-panel    border-border", dot: "#666666" },
  claude_subscription: { label: "Claude.ai", color: "text-blue", bg: "bg-blue/5   border-blue/20", dot: "#5294e0" },
  openai_subscription: { label: "ChatGPT", color: "text-green", bg: "bg-green/5  border-green/20", dot: "#52e07a" },
  gemini_subscription: { label: "Gemini Pro", color: "text-amber", bg: "bg-amber/5  border-amber/20", dot: "#e06c00" }
};
function ProviderCard({ data }) {
  const d = data?.data ?? data ?? {};
  const current = d.current ?? "unknown";
  const model = d.model ?? "";
  const available = d.available ?? [];
  const meta = PROVIDER_META[current] ?? { label: current, color: "text-text", bg: "bg-panel border-border" };
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-elevated border border-border rounded-xl p-4 max-w-md w-full space-y-4", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-widest font-ui", children: "AI Provider" }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: `border rounded-xl px-4 py-3 ${meta.bg}`, children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[9px] uppercase tracking-wider font-ui mb-1", children: "Active" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: `text-[17px] font-ui font-semibold ${meta.color}`, children: meta.label }),
      model && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[11px] font-mono mt-0.5", children: model })
    ] }),
    available.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] uppercase tracking-wider font-ui mb-2", children: "Available" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "space-y-1.5", children: available.map((p2) => {
        const m2 = PROVIDER_META[p2] ?? { label: p2, color: "text-muted", dot: "#444" };
        const isActive = p2 === current;
        return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: `flex items-center gap-2.5 px-3 py-2 rounded-lg border ${isActive ? "border-green/30 bg-green/5" : "border-border bg-panel"}`, children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { style: { width: 6, height: 6, borderRadius: "50%", background: isActive ? "#52e07a" : m2.dot, display: "inline-block", flexShrink: 0 } }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `text-[12px] font-ui ${isActive ? "text-green font-semibold" : m2.color}`, children: m2.label }),
          isActive && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "ml-auto text-green text-[9px] font-ui uppercase tracking-wider", children: "active" })
        ] }, p2);
      }) })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-subtle text-[10px] font-ui", children: [
      "Switch with: ",
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "font-mono text-muted", children: "provider anthropic" }),
      " · ",
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "font-mono text-muted", children: "provider openai" }),
      " · ",
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "font-mono text-muted", children: "provider gemini" })
    ] })
  ] });
}
function Message({ message }) {
  const { role, text, cardType, data } = message;
  if (role === "user") {
    return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex justify-end", children: /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "max-w-lg bg-elevated border border-border rounded-xl px-4 py-2.5\n                        text-text text-sm font-mono", children: text }) });
  }
  if (role === "error") return /* @__PURE__ */ jsxRuntimeExports.jsx(ErrorCard, { text });
  switch (cardType) {
    case "quote":
      return /* @__PURE__ */ jsxRuntimeExports.jsx(QuoteCard, { data });
    case "analysis":
      return /* @__PURE__ */ jsxRuntimeExports.jsx(AnalysisCard, { data });
    case "streaming_analysis":
      return /* @__PURE__ */ jsxRuntimeExports.jsx(StreamingAnalysisCard, { data });
    case "backtest":
      return /* @__PURE__ */ jsxRuntimeExports.jsx(BacktestCard, { data });
    case "flows":
      return /* @__PURE__ */ jsxRuntimeExports.jsx(FlowsCard, { data });
    case "morning_brief":
      return /* @__PURE__ */ jsxRuntimeExports.jsx(MorningBriefCard, { data });
    case "holdings":
      return /* @__PURE__ */ jsxRuntimeExports.jsx(HoldingsCard, { data });
    case "funds":
      return /* @__PURE__ */ jsxRuntimeExports.jsx(FundsCard, { data });
    case "profile":
      return /* @__PURE__ */ jsxRuntimeExports.jsx(ProfileCard, { data });
    case "orders":
      return /* @__PURE__ */ jsxRuntimeExports.jsx(OrdersCard, { data });
    case "alerts":
      return /* @__PURE__ */ jsxRuntimeExports.jsx(AlertsCard, { data });
    case "oi":
      return /* @__PURE__ */ jsxRuntimeExports.jsx(OICard, { data });
    case "patterns":
      return /* @__PURE__ */ jsxRuntimeExports.jsx(PatternsCard, { data });
    case "greeks":
      return /* @__PURE__ */ jsxRuntimeExports.jsx(GreeksCard, { data });
    case "scan":
      return /* @__PURE__ */ jsxRuntimeExports.jsx(ScanCard, { data });
    case "deals":
      return /* @__PURE__ */ jsxRuntimeExports.jsx(DealsCard, { data });
    case "iv_smile":
      return /* @__PURE__ */ jsxRuntimeExports.jsx(IVSmileCard, { data });
    case "gex":
      return /* @__PURE__ */ jsxRuntimeExports.jsx(GEXCard, { data });
    case "delta_hedge":
      return /* @__PURE__ */ jsxRuntimeExports.jsx(DeltaHedgeCard, { data });
    case "risk_report":
      return /* @__PURE__ */ jsxRuntimeExports.jsx(RiskReportCard, { data });
    case "walkforward":
      return /* @__PURE__ */ jsxRuntimeExports.jsx(WalkForwardCard, { data });
    case "whatif":
      return /* @__PURE__ */ jsxRuntimeExports.jsx(WhatIfCard, { data });
    case "strategy":
      return /* @__PURE__ */ jsxRuntimeExports.jsx(StrategyCard, { data });
    case "drift":
      return /* @__PURE__ */ jsxRuntimeExports.jsx(DriftCard, { data });
    case "pairs":
      return /* @__PURE__ */ jsxRuntimeExports.jsx(PairsCard, { data });
    case "memory":
      return /* @__PURE__ */ jsxRuntimeExports.jsx(MemoryCard, { data });
    case "audit":
      return /* @__PURE__ */ jsxRuntimeExports.jsx(AuditCard, { data });
    case "telegram":
      return /* @__PURE__ */ jsxRuntimeExports.jsx(TelegramCard, { data });
    case "provider":
      return /* @__PURE__ */ jsxRuntimeExports.jsx(ProviderCard, { data });
    case "markdown":
    default:
      return /* @__PURE__ */ jsxRuntimeExports.jsx(MarkdownCard, { data });
  }
}
function ChatArea() {
  const messages = useChatStore((s) => s.messages);
  const isLoading = useChatStore((s) => s.isLoading);
  const sidecarError = useChatStore((s) => s.sidecarError);
  const port = useChatStore((s) => s.port);
  const bottomRef = reactExports.useRef(null);
  reactExports.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex-1 overflow-y-auto px-6 py-4 space-y-4", children: [
    messages.length === 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col items-center justify-center h-full gap-3 text-center", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-amber text-4xl", children: "◆" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-text text-lg font-semibold font-ui", children: "India Trade" }),
      sidecarError ? /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-red text-sm max-w-sm font-ui", children: sidecarError }) : port ? /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-sm font-ui", children: "Type a command below or use the sidebar shortcuts." }) : /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-sm font-ui", children: "Starting API server…" })
    ] }),
    messages.map((msg) => /* @__PURE__ */ jsxRuntimeExports.jsx(Message, { message: msg }, msg.id)),
    isLoading && !messages.some((m2) => m2.cardType === "streaming_analysis") && /* @__PURE__ */ jsxRuntimeExports.jsx(ThinkingIndicator, {}),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { ref: bottomRef })
  ] });
}
function ThinkingIndicator() {
  const [secs, setSecs] = reactExports.useState(0);
  reactExports.useEffect(() => {
    const t2 = setInterval(() => setSecs((s) => s + 1), 1e3);
    return () => clearInterval(t2);
  }, []);
  const hint = secs > 15 ? "Running multi-agent analysis — this takes 30–90s…" : secs > 5 ? "Calling AI agents…" : "Thinking…";
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3 bg-elevated border border-border rounded-xl px-4 py-3 max-w-sm", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-amber animate-pulse text-lg", children: "◆" }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-text text-sm font-ui", children: hint }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-muted text-xs font-mono mt-0.5", children: [
        secs,
        "s elapsed"
      ] })
    ] })
  ] });
}
function parseCommand(input) {
  const parts = input.trim().split(/\s+/);
  const cmd = parts[0].toLowerCase();
  const args = parts.slice(1);
  switch (cmd) {
    case "quote":
    case "q":
      if (!args[0]) return { error: "Usage: quote SYMBOL" };
      return { endpoint: "/skills/quote", body: { symbol: args[0].toUpperCase() }, cardType: "quote" };
    case "analyze":
    case "analyse":
    case "a":
      if (!args[0]) return { error: "Usage: analyze SYMBOL" };
      return { stream: true, symbol: args[0].toUpperCase(), exchange: args[1]?.toUpperCase() ?? "NSE" };
    case "morning-brief":
    case "brief":
    case "mb":
      return { endpoint: "/skills/morning_brief", body: {}, cardType: "morning_brief" };
    case "flows":
    case "flow":
      return { endpoint: "/skills/flows", body: {}, cardType: "flows" };
    case "holdings":
    case "h":
      return { endpoint: "/skills/holdings", body: {}, cardType: "holdings" };
    case "positions":
    case "pos":
      return { endpoint: "/skills/positions", body: {}, cardType: "holdings" };
    case "backtest":
    case "bt":
      if (args.length < 2) return { error: "Usage: backtest SYMBOL STRATEGY  (e.g. backtest RELIANCE rsi)" };
      return {
        endpoint: "/skills/backtest",
        body: { symbol: args[0].toUpperCase(), strategy: args[1] },
        cardType: "backtest"
      };
    case "macro":
      return { endpoint: "/skills/macro", body: {}, cardType: "markdown" };
    case "earnings":
      return { endpoint: "/skills/earnings", body: { symbols: args }, cardType: "markdown" };
    case "deep-analyze":
    case "deep-analyse":
    case "da":
      if (!args[0]) return { error: "Usage: deep-analyze SYMBOL [EXCHANGE]" };
      return {
        endpoint: "/skills/deep_analyze",
        body: { symbol: args[0].toUpperCase(), exchange: args[1]?.toUpperCase() ?? "NSE" },
        cardType: "markdown"
      };
    case "funds":
    case "fund":
      return { endpoint: "/skills/funds", body: {}, cardType: "funds" };
    case "profile":
      return { endpoint: "/skills/profile", body: {}, cardType: "profile" };
    case "orders":
    case "order":
      return { endpoint: "/skills/orders", body: {}, cardType: "orders" };
    case "alerts":
    case "al":
      return { endpoint: "/skills/alerts/list", body: {}, cardType: "alerts" };
    case "alert":
      if (args[0] === "remove" || args[0] === "rm") {
        if (!args[1]) return { error: "Usage: alert remove ALERT_ID" };
        return { endpoint: "/skills/alerts/remove", body: { alert_id: args[1] }, cardType: "markdown" };
      }
      if (args.length < 3) return { error: "Usage: alert SYMBOL above|below PRICE" };
      return {
        endpoint: "/skills/alerts/add",
        body: {
          symbol: args[0].toUpperCase(),
          condition: args[1].toLowerCase(),
          // above / below / crosses
          threshold: Number(args[2])
        },
        cardType: "markdown"
      };
    case "oi":
      if (!args[0]) return { error: "Usage: oi SYMBOL [EXCHANGE]" };
      return {
        endpoint: "/skills/oi_profile",
        body: { symbol: args[0].toUpperCase(), exchange: args[1]?.toUpperCase() ?? "NSE" },
        cardType: "oi"
      };
    case "patterns":
    case "pat":
      return { endpoint: "/skills/patterns", body: {}, cardType: "patterns" };
    case "greeks":
    case "greek":
      return { endpoint: "/skills/greeks", body: {}, cardType: "greeks" };
    case "scan":
      return {
        endpoint: "/skills/scan",
        body: { scan_type: args[0] ?? "options", filters: {} },
        cardType: "scan"
      };
    case "deals":
    case "bulk-deals":
      return {
        endpoint: "/skills/deals",
        body: { symbol: args[0]?.toUpperCase() ?? null, days: 5 },
        cardType: "deals"
      };
    case "iv-smile":
    case "smile":
    case "ivsmile": {
      const sym = args[0]?.toUpperCase() ?? "NIFTY";
      return { endpoint: "/skills/iv_smile", body: { symbol: sym, expiry: args[1] ?? null }, cardType: "iv_smile" };
    }
    case "gex": {
      const sym = args[0]?.toUpperCase() ?? "NIFTY";
      return { endpoint: "/skills/gex", body: { symbol: sym, expiry: args[1] ?? null }, cardType: "gex" };
    }
    case "delta-hedge":
    case "dh":
    case "deltahedge":
      return { endpoint: "/skills/delta_hedge", body: {}, cardType: "delta_hedge" };
    case "risk-report":
    case "risk":
    case "var":
      return { endpoint: "/skills/risk_report", body: {}, cardType: "risk_report" };
    case "walkforward":
    case "wf":
    case "walk-forward": {
      const sym = args[0]?.toUpperCase() ?? "NIFTY";
      const strat = args[1] ?? "rsi";
      return { endpoint: "/skills/walkforward", body: { symbol: sym, strategy: strat, window_months: 6 }, cardType: "walkforward" };
    }
    case "whatif":
    case "what-if":
    case "scenario": {
      const sym = args[0]?.toUpperCase();
      const chg = parseFloat(args[1]);
      if (sym && (sym === "NIFTY" || sym === "MARKET") && !isNaN(chg)) {
        return { endpoint: "/skills/whatif", body: { scenario: "market", nifty_change: chg }, cardType: "whatif" };
      } else if (sym && !isNaN(chg)) {
        return { endpoint: "/skills/whatif", body: { scenario: "stock", symbol: sym, stock_change: chg }, cardType: "whatif" };
      }
      return { endpoint: "/skills/whatif", body: { scenario: "market" }, cardType: "whatif" };
    }
    case "strategy":
    case "strat": {
      const sym = args[0]?.toUpperCase() ?? "NIFTY";
      const view = (args[1] ?? "bullish").toUpperCase();
      const dte = parseInt(args[2]) || 30;
      return { endpoint: "/skills/strategy", body: { symbol: sym, view, dte }, cardType: "strategy" };
    }
    case "drift":
      return { endpoint: "/skills/drift", body: {}, cardType: "drift" };
    case "memory":
    case "mem":
      return { endpoint: "/skills/memory", body: {}, cardType: "memory" };
    case "audit": {
      const trade_id = args[0];
      if (!trade_id) return { endpoint: "/skills/memory", body: {}, cardType: "memory" };
      return { endpoint: "/skills/audit", body: { trade_id }, cardType: "audit" };
    }
    case "telegram":
    case "tg":
      return { endpoint: "/skills/telegram/status", body: null, cardType: "telegram", method: "GET" };
    case "provider": {
      if (args[0]) {
        return { endpoint: "/skills/provider/switch", body: { provider: args[0], model: args[1] ?? null }, cardType: "provider" };
      }
      return { endpoint: "/skills/provider", body: {}, cardType: "provider" };
    }
    case "pairs": {
      const symA = args[0]?.toUpperCase() ?? "RELIANCE";
      const symB = args[1]?.toUpperCase() ?? "TCS";
      return { endpoint: "/skills/pairs", body: { stock_a: symA, stock_b: symB }, cardType: "pairs" };
    }
    default:
      return { endpoint: "/skills/chat", body: { message: input }, cardType: "markdown" };
  }
}
function InputBar() {
  const [value, setValue] = reactExports.useState("");
  const { call, get, ready } = useAPI();
  const port = useChatStore((s) => s.port);
  const draft = useChatStore((s) => s.draft);
  const setDraft = useChatStore((s) => s.setDraft);
  const streamCancel = useChatStore((s) => s.streamCancel);
  const setPendingContext = useChatStore((s) => s.setPendingContext);
  const {
    addUserMessage,
    addResponse,
    addError,
    isLoading,
    startStreamingMessage,
    updateStreamingMessage,
    finalizeStreamingMessage,
    setStreamCancel
  } = useChatStore();
  const isStreaming = isLoading && !!streamCancel;
  const inputRef = reactExports.useRef(null);
  reactExports.useEffect(() => {
    if (draft) {
      setValue(draft);
      setDraft("");
      inputRef.current?.focus();
    }
  }, [draft]);
  function runStreaming(symbol, exchange) {
    const msgId = Date.now() + 1;
    startStreamingMessage(msgId, symbol, exchange);
    const url = `http://127.0.0.1:${port}/skills/analyze/stream?symbol=${symbol}&exchange=${exchange}`;
    const es = new EventSource(url);
    function applyEvent(event) {
      if (event.type === "started") {
        updateStreamingMessage(msgId, (d) => ({ ...d, phase: "started" }));
      } else if (event.type === "analyst") {
        updateStreamingMessage(msgId, (d) => ({
          ...d,
          analysts: [...d.analysts, {
            name: event.name,
            verdict: event.verdict,
            confidence: event.confidence,
            error: event.error,
            key_points: event.key_points ?? []
          }]
        }));
      } else if (event.type === "phase") {
        updateStreamingMessage(msgId, (d) => ({ ...d, phase: event.phase }));
      } else if (event.type === "debate_step") {
        updateStreamingMessage(msgId, (d) => ({
          ...d,
          debate_steps: [...d.debate_steps ?? [], { step: event.step, label: event.label, text: event.text }]
        }));
      } else if (event.type === "synthesis_text") {
        updateStreamingMessage(msgId, (d) => ({ ...d, synthesis_text: event.text }));
      } else if (event.type === "done") {
        updateStreamingMessage(msgId, (d) => ({
          ...d,
          phase: "done",
          report: event.report,
          trade_plans: event.trade_plans
        }));
        es.close();
        setStreamCancel(null);
        finalizeStreamingMessage(msgId);
      } else if (event.type === "error") {
        es.close();
        setStreamCancel(null);
        addError(event.message);
        finalizeStreamingMessage(msgId);
      }
    }
    setStreamCancel(() => {
      es.close();
      finalizeStreamingMessage(msgId);
    });
    es.onmessage = (e) => {
      try {
        applyEvent(JSON.parse(e.data));
      } catch (err) {
        console.error("[SSE]", err);
      }
    };
    es.onerror = () => {
      es.close();
      addError("Stream connection lost");
      finalizeStreamingMessage(msgId);
    };
  }
  async function submit() {
    const text = value.trim();
    if (!text || !ready) return;
    if (isStreaming) {
      setValue("");
      setPendingContext(text);
      addUserMessage(text);
      return;
    }
    if (isLoading) return;
    setValue("");
    addUserMessage(text);
    const parsed = parseCommand(text);
    if (parsed.error) {
      addError(parsed.error);
      return;
    }
    if (parsed.stream) {
      runStreaming(parsed.symbol, parsed.exchange);
      return;
    }
    try {
      const result = parsed.method === "GET" ? await get(parsed.endpoint) : await call(parsed.endpoint, parsed.body);
      addResponse({ cardType: parsed.cardType, data: result.data ?? result });
    } catch (e) {
      addError(e.message);
    }
  }
  function onKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }
  const placeholder = !ready ? "Starting API…" : isStreaming ? "Analysis in progress — type to add context…" : "analyze INFY · gex NIFTY · strategy NIFTY bullish · whatif nifty -5 · …";
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex-shrink-0 border-t border-border bg-panel px-4 py-3", children: [
    isStreaming && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "mb-2 px-1 flex items-center gap-2", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-[10px] animate-pulse text-amber font-ui", children: "◆" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-[10px] text-muted font-ui", children: "Analysis running — add context to inject into the follow-up" })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: `flex items-center gap-3 bg-elevated border rounded-xl px-4 py-2.5 ${isStreaming ? "border-amber/30" : "border-border"}`, children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `text-sm font-mono flex-shrink-0 ${isStreaming ? "text-amber animate-pulse" : "text-amber"}`, children: "›" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "input",
        {
          ref: inputRef,
          type: "text",
          value,
          onChange: (e) => setValue(e.target.value),
          onKeyDown,
          placeholder,
          disabled: !ready || isLoading && !isStreaming,
          className: "flex-1 bg-transparent text-text text-sm font-mono outline-none\n                     placeholder:text-subtle disabled:opacity-50",
          autoFocus: true
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "button",
        {
          onClick: submit,
          disabled: !value.trim() || isLoading && !isStreaming || !ready,
          className: "text-amber text-sm font-mono disabled:opacity-30 hover:opacity-80 transition-opacity",
          children: "↵"
        }
      )
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-subtle text-[10px] font-ui mt-1.5 pl-1", children: "analyze INFY · oi NIFTY · greeks · scan · funds · orders · alerts · patterns · da RELIANCE · iv-smile NIFTY · gex NIFTY · delta-hedge · risk-report · walkforward NIFTY rsi · whatif nifty -5 · strategy NIFTY bullish · drift · memory · audit <id> · telegram · provider · pairs RELIANCE TCS" })
  ] });
}
function SetupScreen({ phase, data }) {
  const [showDetails, setShowDetails] = reactExports.useState(false);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(
    "div",
    {
      className: "h-screen w-screen bg-[#0d0d0d] flex flex-col items-center justify-center px-8 text-center select-none",
      style: { WebkitAppRegion: "drag" },
      children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "mb-8", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-4xl", children: "◆" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-text text-xl font-semibold mt-2", children: "India Trade" })
        ] }),
        (phase === "initializing" || phase === "progress") && /* @__PURE__ */ jsxRuntimeExports.jsx(ProgressView, { data }),
        phase === "python_missing" && /* @__PURE__ */ jsxRuntimeExports.jsx(PythonMissingView, { data }),
        phase === "error" && /* @__PURE__ */ jsxRuntimeExports.jsx(ErrorView, { data, showDetails, setShowDetails })
      ]
    }
  );
}
function ProgressView({ data }) {
  const message = data?.message ?? "Starting up...";
  const percent = data?.percent ?? null;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "max-w-md w-full space-y-4", style: { WebkitAppRegion: "no-drag" }, children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-sm font-ui", children: message }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "w-full bg-border rounded-full h-1.5 overflow-hidden", children: percent != null ? /* @__PURE__ */ jsxRuntimeExports.jsx(
      "div",
      {
        className: "bg-amber h-full rounded-full transition-all duration-500 ease-out",
        style: { width: `${percent}%` }
      }
    ) : /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "bg-amber h-full rounded-full w-1/3 animate-pulse" }) }),
    percent != null && /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-muted text-xs font-mono", children: [
      percent,
      "%"
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted/50 text-xs font-ui", children: data?.stage === "installing_deps" ? "This only happens on first launch (~2 min)" : "" })
  ] });
}
function PythonMissingView({ data }) {
  const [copied, setCopied] = reactExports.useState(false);
  function copyBrewCommand() {
    navigator.clipboard.writeText(data?.brewCommand ?? "brew install python@3.12");
    setCopied(true);
    setTimeout(() => setCopied(false), 2e3);
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "max-w-lg w-full space-y-6", style: { WebkitAppRegion: "no-drag" }, children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-amber text-lg font-semibold", children: "Python 3.11+ Required" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-sm font-ui mt-2", children: "India Trade needs Python to run its analysis engine. Install it using one of the options below, then click Retry." })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-1 gap-3", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          onClick: () => window.electronAPI?.openExternal(data?.installUrl ?? "https://www.python.org/downloads/"),
          className: "bg-panel border border-border rounded-lg p-4 text-left hover:border-amber/50 transition-colors cursor-pointer",
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-text text-sm font-semibold", children: "Download from python.org" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-xs mt-1", children: "Official installer — works on all Macs" })
          ]
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-panel border border-border rounded-lg p-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-text text-sm font-semibold", children: "Install with Homebrew" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 mt-2", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("code", { className: "flex-1 bg-elevated text-amber text-xs font-mono px-3 py-2 rounded", children: data?.brewCommand ?? "brew install python@3.12" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "button",
            {
              onClick: copyBrewCommand,
              className: "text-muted hover:text-text text-xs px-2 py-2 border border-border rounded transition-colors cursor-pointer",
              children: copied ? "✓" : "Copy"
            }
          )
        ] })
      ] })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      "button",
      {
        onClick: () => window.electronAPI?.retrySetup(),
        className: "w-full bg-amber/10 border border-amber/30 text-amber text-sm font-ui py-2.5 rounded-lg\n                   hover:bg-amber/20 transition-colors cursor-pointer",
        children: "Retry"
      }
    )
  ] });
}
function ErrorView({ data, showDetails, setShowDetails }) {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "max-w-lg w-full space-y-4", style: { WebkitAppRegion: "no-drag" }, children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-red text-lg font-semibold", children: "Setup Failed" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-sm font-ui mt-2", children: data?.message ?? "An unknown error occurred." })
    ] }),
    data?.details && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "button",
        {
          onClick: () => setShowDetails(!showDetails),
          className: "text-muted text-xs font-ui hover:text-text transition-colors cursor-pointer",
          children: showDetails ? "▼ Hide details" : "▶ Show details"
        }
      ),
      showDetails && /* @__PURE__ */ jsxRuntimeExports.jsx("pre", { className: "mt-2 bg-panel border border-border rounded-lg p-3 text-xs font-mono text-red/80\n                           max-h-48 overflow-y-auto whitespace-pre-wrap", children: data.details })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex gap-3", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "button",
        {
          onClick: () => window.electronAPI?.retrySetup(),
          className: "flex-1 bg-amber/10 border border-amber/30 text-amber text-sm font-ui py-2.5 rounded-lg\n                     hover:bg-amber/20 transition-colors cursor-pointer",
          children: "Retry"
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "button",
        {
          onClick: () => window.electronAPI?.resetVenv(),
          className: "flex-1 bg-red/10 border border-red/30 text-red text-sm font-ui py-2.5 rounded-lg\n                     hover:bg-red/20 transition-colors cursor-pointer",
          children: "Reset Environment"
        }
      )
    ] })
  ] });
}
function StepIndicator({ current, total = 5 }) {
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex items-center gap-2 justify-center py-4", children: Array.from({ length: total }, (_, i) => {
    let cls = "w-2 h-2 rounded-full transition-all duration-300";
    if (i < current) {
      cls += " bg-green";
    } else if (i === current) {
      cls += " bg-amber w-3 h-3";
    } else {
      cls += " bg-subtle";
    }
    return /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: cls }, i);
  }) });
}
function WelcomeStep({ onNext }) {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col items-center justify-center flex-1 gap-6 animate-fade-slide", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-amber text-6xl leading-none", children: "◆" }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-text text-2xl font-semibold font-ui tracking-wide", children: "Welcome to India Trade" }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-sm font-ui max-w-md text-center leading-relaxed", children: "AI-powered trading terminal for Indian markets. NSE, BSE, and F&O with real-time data, AI analysis, and automated strategies." }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      "button",
      {
        onClick: onNext,
        className: "mt-4 px-8 py-2.5 bg-amber text-surface font-ui font-semibold text-sm rounded-lg\n                   hover:brightness-110 transition-all active:scale-95",
        children: "Get Started"
      }
    )
  ] });
}
const PROVIDERS = [
  {
    id: "gemini",
    name: "Google Gemini",
    badge: "Free",
    badgeColor: "bg-green/20 text-green",
    desc: "Free tier at aistudio.google.com",
    keyEnv: "GEMINI_API_KEY",
    keyLabel: "Gemini API key",
    needsKey: true
  },
  {
    id: "anthropic",
    name: "Claude API",
    badge: "API",
    badgeColor: "bg-blue/20 text-blue",
    desc: "Anthropic Claude — pay per token",
    keyEnv: "ANTHROPIC_API_KEY",
    keyLabel: "Anthropic API key",
    needsKey: true
  },
  {
    id: "claude_subscription",
    name: "Claude Pro/Max",
    badge: "Free*",
    badgeColor: "bg-blue/20 text-blue",
    desc: "Uses your Claude subscription — no API key",
    keyEnv: null,
    keyLabel: null,
    needsKey: false,
    setupHint: "Requires: npm i -g @anthropic-ai/claude-code && claude login"
  },
  {
    id: "openai",
    name: "OpenAI",
    badge: "API",
    badgeColor: "bg-green/20 text-green",
    desc: "GPT-4o and compatible endpoints",
    keyEnv: "OPENAI_API_KEY",
    keyLabel: "OpenAI API key",
    needsKey: true
  },
  {
    id: "ollama",
    name: "Ollama",
    badge: "Free",
    badgeColor: "bg-green/20 text-green",
    desc: "Local models — no API key needed",
    keyEnv: null,
    keyLabel: null,
    needsKey: false,
    setupHint: "Requires: brew install ollama && ollama pull llama3.1"
  }
];
function ProviderStep({ formData, setFormData, onNext, port }) {
  const [selected, setSelected] = reactExports.useState(formData.aiProvider || "");
  const [apiKey, setApiKey] = reactExports.useState("");
  const [testing, setTesting] = reactExports.useState(false);
  const [testResult, setTestResult] = reactExports.useState(null);
  const [saved, setSaved] = reactExports.useState(false);
  const base = `http://127.0.0.1:${port}`;
  const provider = PROVIDERS.find((p2) => p2.id === selected);
  const handleTest = async () => {
    if (!provider) return;
    setTesting(true);
    setTestResult(null);
    try {
      const res = await fetch(`${base}/api/onboarding/test-provider`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          provider: provider.id,
          api_key: apiKey,
          model: ""
        })
      });
      const data = await res.json();
      setTestResult(data);
      if (data.ok) {
        await fetch(`${base}/api/onboarding/credential`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ key: "AI_PROVIDER", value: provider.id })
        });
        if (provider.keyEnv && apiKey) {
          await fetch(`${base}/api/onboarding/credential`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ key: provider.keyEnv, value: apiKey })
          });
        }
        setSaved(true);
        setFormData((prev) => ({ ...prev, aiProvider: provider.id }));
      }
    } catch (err) {
      setTestResult({ ok: false, error: err.message });
    } finally {
      setTesting(false);
    }
  };
  const handleSelect = (id2) => {
    setSelected(id2);
    setApiKey("");
    setTestResult(null);
    setSaved(false);
  };
  const canProceed = saved || formData.aiProvider;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col flex-1 gap-6 animate-fade-slide", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "text-center", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-text text-lg font-semibold font-ui", children: "Choose AI Provider" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-xs font-ui mt-1", children: "Powers market analysis, strategy generation, and trade signals" })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid grid-cols-2 gap-3 max-w-xl mx-auto w-full", children: PROVIDERS.map((p2) => /* @__PURE__ */ jsxRuntimeExports.jsxs(
      "button",
      {
        onClick: () => handleSelect(p2.id),
        className: `relative flex flex-col items-start gap-1.5 p-4 rounded-lg border transition-all text-left
              ${selected === p2.id ? "border-amber bg-amber/5" : "border-border bg-panel hover:border-subtle"}`,
        children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 w-full", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-text text-sm font-semibold font-ui", children: p2.name }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `text-[10px] font-ui font-semibold px-1.5 py-0.5 rounded ${p2.badgeColor}`, children: p2.badge })
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-muted text-[11px] font-ui leading-snug", children: p2.desc })
        ]
      },
      p2.id
    )) }),
    selected && provider && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "max-w-lg mx-auto w-full space-y-3", children: provider.needsKey ? /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex gap-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "input",
          {
            type: "password",
            placeholder: `Enter ${provider.name} API key`,
            value: apiKey,
            onChange: (e) => {
              setApiKey(e.target.value);
              setTestResult(null);
              setSaved(false);
            },
            className: "flex-1 bg-elevated border border-border rounded-lg px-3 py-2\n                             text-text text-sm font-mono placeholder:text-subtle\n                             focus:outline-none focus:border-amber"
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: handleTest,
            disabled: !apiKey || testing,
            className: "px-4 py-2 bg-amber/10 text-amber border border-amber/30 rounded-lg\n                             text-sm font-ui font-semibold hover:bg-amber/20 transition-all\n                             disabled:opacity-40 disabled:cursor-not-allowed",
            children: testing ? "Testing..." : "Test Key"
          }
        )
      ] }),
      testResult && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: `text-xs font-ui ${testResult.ok ? "text-green" : "text-red"}`, children: testResult.ok ? testResult.message : testResult.error })
    ] }) : /* @__PURE__ */ jsxRuntimeExports.jsx(
      SetupRunner,
      {
        provider,
        base,
        onComplete: () => {
          setSaved(true);
          setFormData((prev) => ({ ...prev, aiProvider: provider.id }));
          setTestResult({ ok: true, message: `${provider.name} configured` });
        },
        saved
      }
    ) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex justify-end max-w-lg mx-auto w-full mt-auto", children: /* @__PURE__ */ jsxRuntimeExports.jsx(
      "button",
      {
        onClick: onNext,
        disabled: !canProceed,
        className: "px-6 py-2 bg-amber text-surface font-ui font-semibold text-sm rounded-lg\n                     hover:brightness-110 transition-all active:scale-95\n                     disabled:opacity-40 disabled:cursor-not-allowed",
        children: "Next"
      }
    ) })
  ] });
}
function SetupRunner({ provider, base, onComplete, saved }) {
  const [steps, setSteps] = reactExports.useState([]);
  const [running, setRunning] = reactExports.useState(false);
  const [error, setError] = reactExports.useState(null);
  const updateStep = (index, update) => {
    setSteps((prev) => prev.map((s, i) => i === index ? { ...s, ...update } : s));
  };
  const callSetup = async (step) => {
    const res = await fetch(`${base}/api/onboarding/setup-provider`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ provider: provider.id, step })
    });
    return res.json();
  };
  const saveProvider = async () => {
    await fetch(`${base}/api/onboarding/credential`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key: "AI_PROVIDER", value: provider.id })
    });
  };
  const runSetup = async () => {
    setRunning(true);
    setError(null);
    setSteps([]);
    try {
      if (provider.id === "ollama") {
        setSteps([{ label: "Checking if Ollama is installed...", status: "running", output: "" }]);
        const check = await callSetup("check");
        if (!check.installed) {
          updateStep(0, { status: "done", output: "Not installed" });
          setSteps((prev) => [...prev, { label: "Installing Ollama via Homebrew...", status: "running", output: "" }]);
          const install = await callSetup("install");
          if (!install.ok) {
            updateStep(1, { status: "error", output: install.error });
            if (install.download_url) {
              setError({ message: install.error, downloadUrl: install.download_url });
            }
            setRunning(false);
            return;
          }
          updateStep(1, { status: "done", output: install.output || "Installed" });
        } else {
          updateStep(0, { status: "done", output: check.message });
        }
        if (!check.running) {
          setSteps((prev) => [...prev, { label: "Starting Ollama server...", status: "running", output: "" }]);
          const start = await callSetup("start");
          const idx = steps.length;
          setSteps((prev) => prev.map((s, i) => i === prev.length - 1 ? { ...s, status: start.ok ? "done" : "error", output: start.message || start.error } : s));
          if (!start.ok) {
            setRunning(false);
            return;
          }
        }
        const recheck = await callSetup("check");
        if (!recheck.models || recheck.models.length === 0) {
          setSteps((prev) => [...prev, { label: "Downloading llama3.1 (~4GB)...", status: "running", output: "This may take a few minutes" }]);
          const pull = await callSetup("pull_model");
          setSteps((prev) => prev.map((s, i) => i === prev.length - 1 ? { ...s, status: pull.ok ? "done" : "error", output: pull.ok ? "Model ready" : pull.error } : s));
          if (!pull.ok) {
            setRunning(false);
            return;
          }
        }
        await saveProvider();
        setSteps((prev) => [...prev, { label: "Ollama configured", status: "done", output: "" }]);
        onComplete();
      } else if (provider.id === "claude_subscription") {
        setSteps([{ label: "Checking for Claude CLI...", status: "running", output: "" }]);
        const check = await callSetup("check");
        if (!check.installed) {
          updateStep(0, { status: "done", output: "Not installed" });
          setSteps((prev) => [...prev, { label: "Installing Claude CLI via npm...", status: "running", output: "" }]);
          const install = await callSetup("install");
          if (!install.ok) {
            updateStep(1, { status: "error", output: install.error });
            setRunning(false);
            return;
          }
          updateStep(1, { status: "done", output: "Claude CLI installed" });
          if (install.needs_login) {
            setSteps((prev) => [...prev, {
              label: 'Run "claude login" in your terminal to authenticate',
              status: "waiting",
              output: "Open a terminal window and run: claude login"
            }]);
          }
        } else {
          updateStep(0, { status: "done", output: check.message });
        }
        await saveProvider();
        setSteps((prev) => [...prev, { label: "Claude subscription configured", status: "done", output: "" }]);
        onComplete();
      }
    } catch (err) {
      setError({ message: err.message });
    }
    setRunning(false);
  };
  if (saved) {
    return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "space-y-2", children: /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-green text-xs font-ui", children: "Setup complete" }) });
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-3", children: [
    steps.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "bg-elevated border border-border rounded-lg p-3 space-y-2 max-h-48 overflow-y-auto", children: steps.map((step, i) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-start gap-2 text-xs font-mono", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "flex-shrink-0 mt-0.5", children: step.status === "running" ? "..." : step.status === "done" ? /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-green", children: "ok" }) : step.status === "waiting" ? /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-amber", children: "!" }) : step.status === "error" ? /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-red", children: "x" }) : /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-muted", children: "-" }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-text", children: step.label }),
        step.output && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] mt-0.5", children: step.output })
      ] })
    ] }, i)) }),
    error?.downloadUrl && /* @__PURE__ */ jsxRuntimeExports.jsx(
      "button",
      {
        onClick: () => window.electronAPI?.openExternal(error.downloadUrl),
        className: "text-xs text-amber underline font-ui cursor-pointer",
        children: "Download Ollama manually from ollama.com"
      }
    ),
    !saved && /* @__PURE__ */ jsxRuntimeExports.jsx(
      "button",
      {
        onClick: runSetup,
        disabled: running,
        className: "px-4 py-2 bg-amber/10 text-amber border border-amber/30 rounded-lg\n                     text-sm font-ui font-semibold hover:bg-amber/20 transition-all\n                     disabled:opacity-40 disabled:cursor-not-allowed",
        children: running ? "Setting up..." : steps.length > 0 ? "Retry Setup" : "Set Up Automatically"
      }
    )
  ] });
}
const BROKERS = {
  fyers: {
    name: "Fyers",
    badge: "Free",
    badgeColor: "bg-green/20 text-green",
    desc: "Best options chain data — free API",
    portalUrl: "https://myapi.fyers.in",
    portalLabel: "myapi.fyers.in",
    redirectUrl: "http://127.0.0.1:8765/fyers/callback",
    keys: [
      { env: "FYERS_APP_ID", label: "App ID", placeholder: "XXXX-100", secret: false },
      { env: "FYERS_SECRET_KEY", label: "Secret Key", placeholder: "Your secret key", secret: true }
    ],
    steps: [
      "Create a free account at fyers.in (if you don't have one)",
      "Go to myapi.fyers.in → Create App",
      "Set the redirect URL exactly as shown below",
      "Copy your App ID and Secret Key"
    ]
  },
  zerodha: {
    name: "Zerodha",
    badge: "Free*",
    badgeColor: "bg-blue/20 text-blue",
    desc: "Order execution — free Personal plan",
    portalUrl: "https://developers.kite.trade",
    portalLabel: "developers.kite.trade",
    redirectUrl: "http://localhost:8765/zerodha/callback",
    keys: [
      { env: "KITE_API_KEY", label: "API Key", placeholder: "Your API key", secret: false },
      { env: "KITE_API_SECRET", label: "API Secret", placeholder: "Your API secret", secret: true }
    ],
    steps: [
      "Log in at developers.kite.trade",
      "Create App → choose Personal (free) or Connect (Rs 500/mo)",
      "Set the redirect URL exactly as shown below",
      "Copy your API Key and API Secret",
      "Register your static IP on your Zerodha profile (SEBI requirement)"
    ]
  }
};
function MarketDataStep({ formData, setFormData, onNext, port }) {
  const [newsKey, setNewsKey] = reactExports.useState("");
  const [newsTesting, setNewsTesting] = reactExports.useState(false);
  const [newsResult, setNewsResult] = reactExports.useState(null);
  const [newsSaved, setNewsSaved] = reactExports.useState(formData.newsApiSet || false);
  const [brokerConnected, setBrokerConnected] = reactExports.useState(formData.brokerName || "");
  const [expandedBroker, setExpandedBroker] = reactExports.useState(null);
  const [brokerStatus, setBrokerStatus] = reactExports.useState({});
  const [brokerPolling, setBrokerPolling] = reactExports.useState(null);
  const pollRef = reactExports.useRef(null);
  const base = `http://127.0.0.1:${port}`;
  reactExports.useEffect(() => {
    fetch(`${base}/api/status`).then((r2) => r2.json()).then((data) => {
      setBrokerStatus(data);
      for (const key of ["fyers", "zerodha"]) {
        if (data[key]?.authenticated) {
          setBrokerConnected(key);
          setFormData((prev) => ({ ...prev, brokerName: key }));
        }
      }
    }).catch(() => {
    });
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);
  const handleTestNews = async () => {
    setNewsTesting(true);
    setNewsResult(null);
    try {
      const res = await fetch(`${base}/api/onboarding/test-newsapi`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key: newsKey })
      });
      const data = await res.json();
      setNewsResult(data);
      if (data.ok) {
        await fetch(`${base}/api/onboarding/credential`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ key: "NEWSAPI_KEY", value: newsKey })
        });
        setNewsSaved(true);
        setFormData((prev) => ({ ...prev, newsApiSet: true }));
      }
    } catch (err) {
      setNewsResult({ ok: false, error: err.message });
    } finally {
      setNewsTesting(false);
    }
  };
  const handleSaveBrokerKeys = async (brokerId) => {
    const broker = BROKERS[brokerId];
    const inputs = document.querySelectorAll(`[data-broker="${brokerId}"]`);
    const values = {};
    inputs.forEach((input) => {
      values[input.dataset.key] = input.value;
    });
    for (const key of broker.keys) {
      if (!values[key.env]?.trim()) return;
    }
    for (const key of broker.keys) {
      await fetch(`${base}/api/onboarding/credential`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key: key.env, value: values[key.env].trim() })
      });
    }
    handleBrokerLogin(brokerId);
  };
  const handleBrokerLogin = (brokerId) => {
    setBrokerPolling(brokerId);
    const url = `http://127.0.0.1:${port}/${brokerId}/login`;
    if (window.electronAPI?.openExternal) {
      window.electronAPI.openExternal(url);
    } else {
      window.open(url, "_blank");
    }
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${base}/api/status`);
        const data = await res.json();
        setBrokerStatus(data);
        if (data[brokerId]?.authenticated) {
          clearInterval(pollRef.current);
          pollRef.current = null;
          setBrokerPolling(null);
          setBrokerConnected(brokerId);
          setFormData((prev) => ({ ...prev, brokerName: brokerId }));
        }
      } catch {
      }
    }, 2e3);
  };
  const openExternal = (url) => {
    if (window.electronAPI?.openExternal) window.electronAPI.openExternal(url);
    else window.open(url, "_blank");
  };
  const canProceed = newsSaved;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col flex-1 gap-6 animate-fade-slide", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "text-center", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-text text-lg font-semibold font-ui", children: "Market Data" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-xs font-ui mt-1", children: "Connect news and broker data sources" })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "max-w-xl mx-auto w-full space-y-4 overflow-y-auto flex-1", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-panel border border-border rounded-lg p-4 space-y-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("h3", { className: "text-text text-sm font-semibold font-ui", children: "NewsAPI" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[11px] font-ui", children: "Required for AI news analysis" })
          ] }),
          newsSaved && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-green text-xs font-ui font-semibold", children: "Configured" })
        ] }),
        !newsSaved && /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex gap-2", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              "input",
              {
                type: "password",
                placeholder: "Enter NewsAPI key",
                value: newsKey,
                onChange: (e) => {
                  setNewsKey(e.target.value);
                  setNewsResult(null);
                },
                className: "flex-1 bg-elevated border border-border rounded-lg px-3 py-2\n                             text-text text-sm font-mono placeholder:text-subtle\n                             focus:outline-none focus:border-amber"
              }
            ),
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              "button",
              {
                onClick: handleTestNews,
                disabled: !newsKey || newsTesting,
                className: "px-3 py-2 bg-amber/10 text-amber border border-amber/30 rounded-lg\n                             text-xs font-ui font-semibold hover:bg-amber/20 transition-all\n                             disabled:opacity-40 disabled:cursor-not-allowed",
                children: newsTesting ? "Testing..." : "Test"
              }
            )
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "button",
            {
              onClick: () => openExternal("https://newsapi.org/register"),
              className: "text-amber text-[11px] font-ui hover:underline cursor-pointer",
              children: "Get a free key at newsapi.org →"
            }
          ),
          newsResult && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: `text-xs font-ui ${newsResult.ok ? "text-green" : "text-red"}`, children: newsResult.ok ? "NewsAPI key is valid" : newsResult.error })
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-panel border border-border rounded-lg p-4 space-y-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("h3", { className: "text-text text-sm font-semibold font-ui", children: "Broker (Optional)" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[11px] font-ui", children: "Connect for live market data and trading" })
          ] }),
          brokerConnected && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-green text-xs font-ui font-semibold capitalize", children: [
            brokerConnected,
            " connected"
          ] })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "bg-elevated border border-border rounded-lg p-3", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-muted text-[11px] font-ui leading-relaxed", children: [
          "Without a broker, you get 15-min delayed data and paper trading only. A broker gives you ",
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-text", children: "live quotes, options chain, and real order execution" }),
          "."
        ] }) }),
        !brokerConnected && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "space-y-2", children: Object.entries(BROKERS).map(([id2, broker]) => {
          const isExpanded = expandedBroker === id2;
          const isConfigured = brokerStatus[id2]?.configured;
          const isPolling = brokerPolling === id2;
          return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "border border-border rounded-lg overflow-hidden", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsxs(
              "button",
              {
                onClick: () => setExpandedBroker(isExpanded ? null : id2),
                className: `w-full flex items-center justify-between p-4 bg-elevated
                                 hover:border-amber/50 transition-all text-left border-b
                                 ${isExpanded ? "border-amber/30" : "border-transparent"}`,
                children: [
                  /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
                    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
                      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-text text-sm font-semibold font-ui", children: broker.name }),
                      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `text-[10px] font-ui font-semibold px-1.5 py-0.5 rounded ${broker.badgeColor}`, children: broker.badge }),
                      isConfigured && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-green text-[10px] font-ui", children: "Keys set" })
                    ] }),
                    /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-muted text-[11px] font-ui mt-0.5 block", children: broker.desc })
                  ] }),
                  /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `px-3 py-1.5 rounded-lg text-xs font-ui font-semibold transition-all
                        ${isExpanded ? "bg-amber/10 text-amber border border-amber/30" : "bg-elevated text-muted border border-border hover:text-text"}`, children: isExpanded ? "Hide" : "Set Up" })
                ]
              }
            ),
            isExpanded && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "p-3 border-t border-border space-y-3 bg-panel", children: [
              isConfigured ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-2", children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-green text-xs font-ui", children: "API keys configured. Click to authenticate." }),
                /* @__PURE__ */ jsxRuntimeExports.jsx(
                  "button",
                  {
                    onClick: () => handleBrokerLogin(id2),
                    disabled: isPolling,
                    className: "px-4 py-2 bg-green/10 text-green border border-green/30 rounded-lg\n                                         text-sm font-ui font-semibold hover:bg-green/20 transition-all\n                                         disabled:opacity-40 w-full",
                    children: isPolling ? "Waiting for login..." : "Connect"
                  }
                )
              ] }) : /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
                /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-1.5", children: [
                  /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] font-ui uppercase tracking-wider", children: "Setup Guide" }),
                  broker.steps.map((step, i) => /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-muted text-[11px] font-ui flex gap-2", children: [
                    /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-amber flex-shrink-0", children: [
                      i + 1,
                      "."
                    ] }),
                    /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: step })
                  ] }, i))
                ] }),
                /* @__PURE__ */ jsxRuntimeExports.jsxs(
                  "button",
                  {
                    onClick: () => openExternal(broker.portalUrl),
                    className: "w-full px-3 py-2 bg-amber/10 text-amber border border-amber/30\n                                         rounded-lg text-xs font-ui font-semibold hover:bg-amber/20\n                                         transition-all cursor-pointer",
                    children: [
                      "Open ",
                      broker.portalLabel,
                      " →"
                    ]
                  }
                ),
                /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
                  /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[10px] font-ui mb-1", children: "Redirect URL (copy this exactly):" }),
                  /* @__PURE__ */ jsxRuntimeExports.jsx(CopyableCode, { text: broker.redirectUrl })
                ] }),
                /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "space-y-2", children: broker.keys.map((key) => /* @__PURE__ */ jsxRuntimeExports.jsx(
                  "input",
                  {
                    "data-broker": id2,
                    "data-key": key.env,
                    type: key.secret ? "password" : "text",
                    placeholder: key.label + ": " + key.placeholder,
                    className: "w-full bg-elevated border border-border rounded-lg px-3 py-2\n                                             text-text text-sm font-mono placeholder:text-subtle\n                                             focus:outline-none focus:border-amber"
                  },
                  key.env
                )) }),
                /* @__PURE__ */ jsxRuntimeExports.jsx(
                  "button",
                  {
                    onClick: () => handleSaveBrokerKeys(id2),
                    disabled: isPolling,
                    className: "w-full px-4 py-2 bg-green/10 text-green border border-green/30\n                                         rounded-lg text-sm font-ui font-semibold hover:bg-green/20\n                                         transition-all disabled:opacity-40",
                    children: isPolling ? "Waiting for login..." : "Save & Connect"
                  }
                )
              ] }),
              isPolling && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-amber text-[10px] font-ui animate-pulse text-center", children: "Complete the login in your browser..." })
            ] })
          ] }, id2);
        }) })
      ] })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex justify-between max-w-xl mx-auto w-full", children: [
      !brokerConnected && !brokerPolling && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-muted text-[11px] font-ui self-center", children: "You can connect a broker later from Settings" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "ml-auto", children: /* @__PURE__ */ jsxRuntimeExports.jsx(
        "button",
        {
          onClick: onNext,
          disabled: !canProceed,
          className: "px-6 py-2 bg-amber text-surface font-ui font-semibold text-sm rounded-lg\n                       hover:brightness-110 transition-all active:scale-95\n                       disabled:opacity-40 disabled:cursor-not-allowed",
          children: "Next"
        }
      ) })
    ] })
  ] });
}
function CopyableCode({ text }) {
  const [copied, setCopied] = reactExports.useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2e3);
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("code", { className: "flex-1 bg-elevated text-amber text-[11px] font-mono px-3 py-2 rounded border border-border truncate", children: text }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      "button",
      {
        onClick: handleCopy,
        className: "text-muted hover:text-text text-xs px-2 py-2 border border-border rounded\n                   transition-colors cursor-pointer flex-shrink-0",
        children: copied ? "Copied" : "Copy"
      }
    )
  ] });
}
function TradingSettingsStep({ formData, setFormData, onNext }) {
  const [capital, setCapital] = reactExports.useState(formData.capital || 2e5);
  const [riskPct, setRiskPct] = reactExports.useState(formData.riskPct || 2);
  const [mode, setMode] = reactExports.useState(formData.tradingMode || "PAPER");
  const handleNext = () => {
    setFormData((prev) => ({
      ...prev,
      capital,
      riskPct,
      tradingMode: mode
    }));
    onNext();
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col flex-1 gap-6 animate-fade-slide", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "text-center", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-text text-lg font-semibold font-ui", children: "Trading Settings" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-xs font-ui mt-1", children: "Configure your capital and risk parameters" })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "max-w-md mx-auto w-full space-y-5", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "text-text text-sm font-ui font-semibold block", children: "Trading Capital (INR)" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "input",
          {
            type: "number",
            value: capital,
            onChange: (e) => setCapital(Number(e.target.value) || 0),
            min: 0,
            step: 1e4,
            className: "w-full bg-elevated border border-border rounded-lg px-3 py-2.5\n                       text-text text-sm font-mono\n                       focus:outline-none focus:border-amber"
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[11px] font-ui", children: "Total capital allocated for trading. Used for position sizing." })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "text-text text-sm font-ui font-semibold block", children: "Risk Per Trade (%)" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "input",
          {
            type: "number",
            value: riskPct,
            onChange: (e) => setRiskPct(Number(e.target.value) || 0),
            min: 0.1,
            max: 10,
            step: 0.5,
            className: "w-full bg-elevated border border-border rounded-lg px-3 py-2.5\n                       text-text text-sm font-mono\n                       focus:outline-none focus:border-amber"
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[11px] font-ui", children: "Maximum percentage of capital risked per trade. 1-2% recommended." })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "text-text text-sm font-ui font-semibold block", children: "Trading Mode" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex gap-3", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "button",
            {
              onClick: () => setMode("PAPER"),
              className: `flex-1 py-2.5 rounded-lg border text-sm font-ui font-semibold transition-all
                ${mode === "PAPER" ? "border-amber bg-amber/10 text-amber" : "border-border bg-elevated text-muted hover:border-subtle"}`,
              children: "Paper Trading"
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "button",
            {
              onClick: () => setMode("LIVE"),
              className: `flex-1 py-2.5 rounded-lg border text-sm font-ui font-semibold transition-all
                ${mode === "LIVE" ? "border-red bg-red/10 text-red" : "border-border bg-elevated text-muted hover:border-subtle"}`,
              children: "Live Trading"
            }
          )
        ] }),
        mode === "LIVE" && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-red text-[11px] font-ui", children: "Live mode executes real trades with real money. Make sure your broker is connected and you understand the risks." }),
        mode === "PAPER" && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-[11px] font-ui", children: "Paper mode simulates trades without real money. Recommended for getting started." })
      ] })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex justify-end max-w-md mx-auto w-full mt-auto", children: /* @__PURE__ */ jsxRuntimeExports.jsx(
      "button",
      {
        onClick: handleNext,
        className: "px-6 py-2 bg-amber text-surface font-ui font-semibold text-sm rounded-lg\n                     hover:brightness-110 transition-all active:scale-95",
        children: "Next"
      }
    ) })
  ] });
}
function CompletionStep({ formData, onComplete, completing }) {
  const providerNames = {
    gemini: "Google Gemini",
    anthropic: "Claude (Anthropic)",
    openai: "OpenAI",
    ollama: "Ollama (Local)"
  };
  const formatCurrency = (val) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(val || 2e5);
  };
  const items = [
    {
      label: "AI Provider",
      value: providerNames[formData.aiProvider] || formData.aiProvider || "Not set",
      ok: !!formData.aiProvider
    },
    {
      label: "NewsAPI",
      value: formData.newsApiSet ? "Configured" : "Not set",
      ok: !!formData.newsApiSet
    },
    {
      label: "Broker",
      value: formData.brokerName ? formData.brokerName.charAt(0).toUpperCase() + formData.brokerName.slice(1) : "Skipped",
      ok: !!formData.brokerName,
      skipped: !formData.brokerName
    },
    {
      label: "Capital",
      value: formatCurrency(formData.capital),
      ok: true
    },
    {
      label: "Risk",
      value: `${formData.riskPct || 2}%`,
      ok: true
    },
    {
      label: "Mode",
      value: formData.tradingMode === "LIVE" ? "Live" : "Paper",
      ok: true
    }
  ];
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col items-center flex-1 gap-6 animate-fade-slide", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "text-center", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-green text-4xl leading-none block mb-3", children: "✓" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-text text-lg font-semibold font-ui", children: "All Set" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-muted text-xs font-ui mt-1", children: "Here is a summary of your configuration" })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "bg-panel border border-border rounded-lg p-4 max-w-md w-full space-y-3", children: items.map((item) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-muted text-sm font-ui", children: item.label }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `text-sm font-mono ${item.ok ? "text-text" : "text-subtle"}`, children: item.value }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `text-xs ${item.skipped ? "text-subtle" : item.ok ? "text-green" : "text-red"}`, children: item.skipped ? "⊘" : item.ok ? "✓" : "✗" })
      ] })
    ] }, item.label)) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      "button",
      {
        onClick: onComplete,
        disabled: completing,
        className: "mt-4 px-8 py-2.5 bg-amber text-surface font-ui font-semibold text-sm rounded-lg\n                   hover:brightness-110 transition-all active:scale-95\n                   disabled:opacity-60 disabled:cursor-not-allowed",
        children: completing ? "Saving..." : "Start Trading"
      }
    )
  ] });
}
const TOTAL_STEPS = 5;
function OnboardingWizard({ port, onComplete }) {
  const [step, setStep] = reactExports.useState(0);
  const [completing, setCompleting] = reactExports.useState(false);
  const [formData, setFormData] = reactExports.useState({
    aiProvider: "",
    newsApiSet: false,
    brokerName: "",
    capital: 2e5,
    riskPct: 2,
    tradingMode: "PAPER"
  });
  const base = `http://127.0.0.1:${port}`;
  const handleComplete = async () => {
    setCompleting(true);
    try {
      await fetch(`${base}/api/onboarding/complete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          capital: formData.capital || 2e5,
          risk_pct: formData.riskPct || 2,
          trading_mode: formData.tradingMode || "PAPER"
        })
      });
      onComplete();
    } catch (err) {
      console.error("Failed to complete onboarding:", err);
      setCompleting(false);
    }
  };
  const next = () => setStep((s) => Math.min(s + 1, TOTAL_STEPS - 1));
  const renderStep = () => {
    switch (step) {
      case 0:
        return /* @__PURE__ */ jsxRuntimeExports.jsx(WelcomeStep, { onNext: next });
      case 1:
        return /* @__PURE__ */ jsxRuntimeExports.jsx(
          ProviderStep,
          {
            formData,
            setFormData,
            onNext: next,
            port
          }
        );
      case 2:
        return /* @__PURE__ */ jsxRuntimeExports.jsx(
          MarketDataStep,
          {
            formData,
            setFormData,
            onNext: next,
            port
          }
        );
      case 3:
        return /* @__PURE__ */ jsxRuntimeExports.jsx(
          TradingSettingsStep,
          {
            formData,
            setFormData,
            onNext: next
          }
        );
      case 4:
        return /* @__PURE__ */ jsxRuntimeExports.jsx(
          CompletionStep,
          {
            formData,
            onComplete: handleComplete,
            completing
          }
        );
      default:
        return null;
    }
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col h-full bg-surface", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "drag h-[52px] flex items-center justify-center flex-shrink-0 bg-panel border-b border-border", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "w-[76px] flex-shrink-0" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex-1 flex items-center justify-center gap-2 pointer-events-none", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-amber text-[15px]", children: "◆" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-text text-[13px] font-semibold tracking-wide font-ui", children: "India Trade" })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "w-[76px] flex-shrink-0" })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(StepIndicator, { current: step, total: TOTAL_STEPS }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex-1 flex flex-col px-8 pb-8 overflow-y-auto", children: renderStep() })
  ] });
}
function App() {
  const { setPort, setSidecarError, setBrokerStatuses } = useChatStore();
  const port = useChatStore((s) => s.port);
  const [setupPhase, setSetupPhase] = reactExports.useState("initializing");
  const [setupData, setSetupData] = reactExports.useState(null);
  reactExports.useEffect(() => {
    if (window.__INDIA_TRADE_WEB__) {
      const checkReady = async () => {
        try {
          const res = await fetch("/api/onboarding/status");
          if (res.status === 401) {
            window.location.href = "/";
            return;
          }
          const data = await res.json();
          setPort(0);
          if (data.onboarding_complete) {
            setSetupPhase("ready");
          } else {
            setSetupPhase("onboarding");
          }
        } catch {
          setSetupPhase("error");
          setSetupData({ message: "Cannot connect to server" });
        }
      };
      checkReady();
      return;
    }
    window.electronAPI?.onSetupProgress((data) => {
      setSetupPhase("progress");
      setSetupData(data);
    });
    window.electronAPI?.onSetupPythonMissing((data) => {
      setSetupPhase("python_missing");
      setSetupData(data);
    });
    window.electronAPI?.onSidecarReady(async ({ port: port2 }) => {
      setPort(port2);
      try {
        const res = await fetch(`http://127.0.0.1:${port2}/api/onboarding/status`);
        const data = await res.json();
        if (data.onboarding_complete) {
          setSetupPhase("ready");
        } else {
          setSetupPhase("onboarding");
        }
      } catch {
        setSetupPhase("ready");
      }
    });
    window.electronAPI?.onSidecarError(({ message, details }) => {
      setSidecarError(message);
      if (setupPhase !== "ready") {
        setSetupPhase("error");
        setSetupData({ message, details });
      }
    });
    window.electronAPI?.getPort().then(async (port2) => {
      if (port2) {
        setPort(port2);
        try {
          const res = await fetch(`http://127.0.0.1:${port2}/api/onboarding/status`);
          const data = await res.json();
          if (data.onboarding_complete) {
            setSetupPhase("ready");
          } else {
            setSetupPhase("onboarding");
          }
        } catch {
          setSetupPhase("ready");
        }
      }
    });
  }, []);
  reactExports.useEffect(() => {
    if (!port && port !== 0) return;
    const statusUrl = window.__INDIA_TRADE_WEB__ ? "/api/status" : `http://127.0.0.1:${port}/api/status`;
    const fetchStatus = () => fetch(statusUrl).then((r2) => r2.json()).then(setBrokerStatuses).catch(() => {
    });
    fetchStatus();
    const t2 = setInterval(fetchStatus, 8e3);
    return () => clearInterval(t2);
  }, [port]);
  if (setupPhase === "onboarding") {
    return /* @__PURE__ */ jsxRuntimeExports.jsx(OnboardingWizard, { port, onComplete: () => setSetupPhase("ready") });
  }
  if (setupPhase !== "ready") {
    return /* @__PURE__ */ jsxRuntimeExports.jsx(SetupScreen, { phase: setupPhase, data: setupData });
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col h-full bg-surface", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "drag flex items-center h-[52px] bg-panel border-b border-border flex-shrink-0", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "w-[76px] flex-shrink-0" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex-1 flex items-center justify-center gap-2 pointer-events-none", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-amber text-[15px]", children: "◆" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-text text-[13px] font-semibold tracking-wide font-ui", children: "India Trade" })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "no-drag flex items-center gap-3 pr-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(MarketBadge, {}),
        /* @__PURE__ */ jsxRuntimeExports.jsx(StatusDot, {})
      ] })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-1 overflow-hidden", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(Sidebar, {}),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col flex-1 overflow-hidden", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(ChatArea, {}),
        /* @__PURE__ */ jsxRuntimeExports.jsx(InputBar, {})
      ] })
    ] })
  ] });
}
function MarketBadge() {
  const { status, nifty } = useMarketClock();
  const cfg = {
    "open": { dot: "bg-green animate-pulse", label: "Open", text: "text-green" },
    "pre-open": { dot: "bg-amber animate-pulse", label: "Pre-open", text: "text-amber" },
    "post-close": { dot: "bg-amber", label: "Post-close", text: "text-amber" },
    "closed": { dot: "bg-subtle", label: "Closed", text: "text-subtle" }
  }[status] ?? { dot: "bg-subtle", label: "", text: "text-subtle" };
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-1.5", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `w-1.5 h-1.5 rounded-full ${cfg.dot}` }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `text-[11px] font-ui ${cfg.text}`, children: nifty ? `N ${nifty}` : cfg.label })
  ] });
}
function StatusDot() {
  const { port, sidecarError } = useChatStore();
  const connected = !!port && !sidecarError;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `w-2 h-2 rounded-full transition-all ${connected ? "bg-green shadow-[0_0_6px_rgba(82,224,122,0.5)]" : "bg-subtle"}` }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-muted text-[11px] font-ui", children: sidecarError ? "error" : connected ? "connected" : "starting..." })
  ] });
}
client.createRoot(document.getElementById("root")).render(
  /* @__PURE__ */ jsxRuntimeExports.jsx(React.StrictMode, { children: /* @__PURE__ */ jsxRuntimeExports.jsx(App, {}) })
);
