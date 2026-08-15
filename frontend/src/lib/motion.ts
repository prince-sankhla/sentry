/**
 * Shared Framer Motion vocabulary.
 *
 * One easing curve and one set of transitions across the platform, so every
 * surface feels like it was animated by the same hand. The curve is the
 * landing page's — promoted here and reused everywhere.
 *
 * House rules: micro-interactions only. Hover lifts a few pixels, scale stays
 * inside 1.01–1.02, opacity is smooth, nothing bounces for decoration.
 */

/** The platform easing curve — matches `--ease-out-quint` in globals.css. */
export const EASE = [0.22, 1, 0.36, 1] as const;

/** Springy variant, for layout-driven motion like the active-nav pill. */
export const SPRING = { type: "spring", stiffness: 420, damping: 34 } as const;

/** Softer spring for hover elevation. */
export const SPRING_SOFT = { type: "spring", stiffness: 300, damping: 24 } as const;

export const DURATION = {
  fast: 0.18,
  base: 0.26,
  slow: 0.5,
  entrance: 0.7
} as const;

/* ------------------------------------------------------------------ variants */

/**
 * Staggered rise. Pass the index via `custom` to cascade a list:
 *   <motion.div custom={i} variants={fadeUp} initial="hidden" animate="show" />
 */
export const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  show: (i = 0) => ({
    opacity: 1,
    y: 0,
    transition: { duration: DURATION.entrance, delay: 0.1 + i * 0.08, ease: EASE }
  })
};

/** Shorter rise for in-app content — less theatrical than the marketing one. */
export const rise = {
  hidden: { opacity: 0, y: 8 },
  show: (i = 0) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.42, delay: i * 0.04, ease: EASE }
  })
};

/** Plain cross-fade. */
export const fade = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { duration: DURATION.base, ease: EASE } },
  exit: { opacity: 0, transition: { duration: DURATION.fast, ease: EASE } }
};

/** Floating panel / dialog entrance. */
export const panelIn = {
  hidden: { opacity: 0, y: 10, scale: 0.985 },
  show: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { duration: DURATION.base, ease: EASE }
  },
  exit: {
    opacity: 0,
    y: 6,
    scale: 0.99,
    transition: { duration: DURATION.fast, ease: EASE }
  }
};

/** Container that cascades its children. Pair with `rise` on each child. */
export const stagger = {
  hidden: {},
  show: { transition: { staggerChildren: 0.05, delayChildren: 0.04 } }
};

/* -------------------------------------------------------------- interactions */

/** Standard card hover: a small lift, nothing more. */
export const hoverLift = {
  whileHover: { y: -3 },
  transition: SPRING_SOFT
} as const;

/** Standard pressable: barely-there scale, inside the 1.01–1.02 band. */
export const pressable = {
  whileHover: { scale: 1.01 },
  whileTap: { scale: 0.985 },
  transition: SPRING_SOFT
} as const;
