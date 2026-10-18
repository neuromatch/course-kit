// mdast helpers shared by the plugins.

export const text = (value) => ({ type: 'text', value });

// [node, is top level] for every node of `type`, in document order.
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

// Replace a node in place (transforms only get the tree, not parents).
export function replaceNode(node, replacement) {
  for (const key of Object.keys(node)) delete node[key];
  Object.assign(node, replacement);
}
