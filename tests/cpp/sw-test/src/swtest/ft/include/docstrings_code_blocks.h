#pragma once

/**
 * A class with examples.
 * <pre>
 * +---+
 * | x |
 * +---+
 * </pre>
 * Create an instance:
 * @code{.cpp}
 * DocCodeBlocks item;
 * @endcode
 */
struct DocCodeBlocks {
  /** Set the value:
   * <pre><code>
   * item.value = 5;
   * </code></pre>
   */
  int value = 0;
  /**
   * Compute the next value.
   *
   * @param x Input value.
   * @return Result value.
   *
   * @code{.cpp}
   * auto result = item.example(1);
   * @endcode
   */
  int example(int x) { return x + 1; }

  /** Integer overload.
   * @code
   * item.overloaded(1);
   * @endcode
   */
  int overloaded(int x) { return x; }

  /** Floating overload.
   * @code
   * item.overloaded(1.5);
   * @endcode
   */
  double overloaded(double x) { return x; }

  /** Boolean overload.
   * @code
   * item.overloaded(true);
   * @endcode
   */
  bool overloaded(bool x) { return x; }

  /** @code item.overridden(1); @endcode */
  int overridden(int x) { return x; }
};

/** Function examples: @code int x = doc_code_function(); @endcode
 * Another example:
 * ```cpp
 * auto value = doc_code_function();
 * ```
 */
inline int doc_code_function() { return 42; }

/** @code{.cpp} auto x = doc_code_unchanged(); @endcode */
inline int doc_code_unchanged() { return 1; }

/** @code{.cpp} auto x = doc_code_disabled(); @endcode */
inline int doc_code_disabled() { return 2; }

/** Enum examples.
 * @code{.cpp}
 * auto e = DocCodeEnum::Ready;
 * @endcode
 */
enum class DocCodeEnum {
  /** Use this value.
   * @code
   * auto value = DocCodeEnum::Ready;
   * @endcode
   */
  Ready
};

/** Templated example.
 * \code{.cpp}
 * DocCodeTemplate<int> instance;
 * \endcode
 */
template <typename T>
struct DocCodeTemplate {
  T echo(T value) { return value; }
};
