// mdast helpers shared by the plugins.

/** An mdast text node. */
export const text = (value) => ({ type: 'text', value });

/**
 * Find every node of `type`, in document order.
 * @param {object} tree mdast root
 * @param {string} type node type to look for
 * @returns {Array<[object, boolean]>} [node, isTopLevel] pairs; top level means directly under the root or a block
 */
export function findPlaceholders(tree, type) {
  const found = [];
  const walk = (node, ancestors) => {
    (node.children ?? []).forEach((child) => {
      if (child.type === type) {
        found.push([child, ancestors.every((a) => a.type === 'root' || a.type === 'block')]);
      } else {
        walk(child, [...ancestors, child]);
      }
    });
  };
  walk(tree, [tree]);
  return found;
}

/**
 * Replace a node in place: transforms only get the tree, not parents, so the
 * node's own keys are swapped for the replacement's.
 * @param {object} node node to overwrite
 * @param {object} replacement node whose keys it takes
 */
export function replaceNode(node, replacement) {
  for (const key of Object.keys(node)) delete node[key];
  Object.assign(node, replacement);
}
