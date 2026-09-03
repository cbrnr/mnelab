# © MNELAB developers
#
# License: BSD (3-clause)

"""Create History entries for edited events and annotations."""

import numpy as np


def events_history(old, new, row_ids):
    """Return History code that transforms old events into new events."""
    if np.array_equal(old, new):
        return None
    if len(new) == 0:
        return "data.events = np.empty((0, 3), dtype=int)"
    if len(new) != len(row_ids) or not _valid_row_ids(row_ids) or len(old) == 0:
        return f"data.events = np.array({new.tolist()}, dtype=int)"

    final = dict(zip(row_ids, new))
    kept = [row_id for row_id in range(len(old)) if row_id in final]
    added = [row_id for row_id in row_ids if row_id >= len(old)]
    history = []

    for column in range(3):
        changed = [
            row_id for row_id in kept if old[row_id, column] != final[row_id][column]
        ]
        values = [int(final[row_id][column]) for row_id in changed]
        history.extend(_assignments("data.events", column, changed, values))

    history.extend(_remove_events(len(old), kept))
    current = kept
    wanted = [row_id for row_id in row_ids if row_id < len(old)]
    if current != wanted:
        sorted_ids = sorted(current, key=lambda row_id: final[row_id][0])
        if sorted_ids == wanted:
            history.append(
                "data.events = data.events["
                'np.argsort(data.events[:, 0], kind="stable")]'
            )
        else:
            order = [current.index(row_id) for row_id in wanted]
            history.append(f"data.events = data.events[{order}]")

    for index, row_id in enumerate(row_ids):
        if row_id in added:
            row = [int(value) for value in final[row_id]]
            history.append(
                f"data.events = np.insert(data.events, {index}, {row}, axis=0)"
            )

    return "\n".join(history)


def annotations_history(old, new, row_ids):
    """Return History code that transforms old annotations into new annotations."""
    if _annotations_equal(old, new):
        return None
    if len(new) == 0:
        return "data.set_annotations(None)"
    if len(new) != len(row_ids) or not _valid_row_ids(row_ids):
        return _set_annotations_history(new)

    final = dict(zip(row_ids, zip(new.onset, new.duration, new.description)))
    kept = [row_id for row_id in range(len(old)) if row_id in final]
    added = [row_id for row_id in row_ids if row_id >= len(old)]
    history = []

    descriptions = [str(final[row_id][2]) for row_id in kept]
    old_length = old.description.dtype.itemsize // 4
    if descriptions and max(map(len, descriptions)) > old_length:
        length = max(
            max(map(len, old.description), default=0), max(map(len, descriptions))
        )
        history.append(
            "data.annotations.description = "
            f'data.annotations.description.astype("<U{length}")'
        )

    for column, field in enumerate(("onset", "duration", "description")):
        changed = [
            row_id
            for row_id in kept
            if getattr(old, field)[row_id] != final[row_id][column]
        ]
        convert = str if field == "description" else float
        values = [convert(final[row_id][column]) for row_id in changed]
        history.extend(_assignments(f"data.annotations.{field}", None, changed, values))

    history.extend(_remove_annotations(len(old), kept))
    current = kept
    wanted = [row_id for row_id in row_ids if row_id < len(old)]
    if current != wanted:
        sorted_ids = sorted(
            current, key=lambda row_id: (final[row_id][0], final[row_id][1])
        )
        if sorted_ids == wanted:
            history.append(
                "order = np.lexsort((data.annotations.duration, "
                "data.annotations.onset))\n"
                "data.set_annotations(data.annotations[order])"
            )
        else:
            order = [current.index(row_id) for row_id in wanted]
            history.append(f"data.set_annotations(data.annotations[{order}])")

    if added:
        rows = [final[row_id] for row_id in added]
        onset, duration, description = zip(*rows)
        history.append(
            "data.annotations.append("
            f"{[float(value) for value in onset]}, "
            f"{[float(value) for value in duration]}, "
            f"{[str(value) for value in description]})"
        )

        appended = wanted + added
        appended = sorted(
            appended,
            key=lambda row_id: (final[row_id][0], final[row_id][1]),
        )
        if appended != row_ids:
            order = [appended.index(row_id) for row_id in row_ids]
            history.append(f"data.set_annotations(data.annotations[{order}])")

    return "\n".join(history)


def _valid_row_ids(row_ids):
    """Return whether row IDs unambiguously identify old and added rows."""
    return len(row_ids) == len(set(row_ids)) and all(
        isinstance(row_id, int) and row_id >= 0 for row_id in row_ids
    )


def _remove_events(old_length, kept):
    """Return compact event removal code."""
    removed = [index for index in range(old_length) if index not in kept]
    if not removed:
        return []
    if len(kept) <= len(removed):
        indices = _index_expression(kept, selection=True)
        return [f"data.events = data.events[{indices}]"]
    return [
        f"data.events = np.delete(data.events, {_index_expression(removed)}, axis=0)"
    ]


def _remove_annotations(old_length, kept):
    """Return compact annotation removal code."""
    removed = [index for index in range(old_length) if index not in kept]
    if not removed:
        return []
    if len(kept) <= len(removed):
        indices = _index_expression(kept, selection=True)
        return [f"data.set_annotations(data.annotations[{indices}])"]
    return [f"data.annotations.delete({_index_expression(removed)})"]


def _assignments(target, column, indices, values):
    """Return assignments, combining consecutive indices into slices."""
    history = []
    offset = 0
    for group in _index_groups(indices):
        group_values = values[offset : offset + len(group)]
        offset += len(group)
        index = str(group[0])
        value = repr(group_values[0])
        if len(group) > 1:
            index = f"{group[0]}:{group[-1] + 1}"
            value = repr(group_values)
        if column is None:
            history.append(f"{target}[{index}] = {value}")
        else:
            history.append(f"{target}[{index}, {column}] = {value}")
    return history


def _index_expression(indices, *, selection=False):
    """Return a compact index expression."""
    groups = _index_groups(indices)
    if len(groups) == 1 and (selection or len(groups[0]) > 1):
        return f"{groups[0][0]}:{groups[0][-1] + 1}"
    if any(len(group) > 1 for group in groups):
        parts = [
            f"{group[0]}:{group[-1] + 1}" if len(group) > 1 else str(group[0])
            for group in groups
        ]
        return f"np.r_[{', '.join(parts)}]"
    return str(indices)


def _index_groups(indices):
    """Return consecutive groups of sorted indices."""
    groups = []
    for index in indices:
        if groups and index == groups[-1][-1] + 1:
            groups[-1].append(index)
        else:
            groups.append([index])
    return groups


def _set_annotations_history(annotations):
    """Return code that replaces all annotations."""
    return (
        "data.set_annotations(mne.Annotations("
        f"{annotations.onset.tolist()}, {annotations.duration.tolist()}, "
        f"{annotations.description.tolist()}))"
    )


def _annotations_equal(first, second):
    """Return whether two annotations objects contain the same segments."""
    return (
        np.array_equal(first.onset, second.onset)
        and np.array_equal(first.duration, second.duration)
        and np.array_equal(first.description, second.description)
    )
