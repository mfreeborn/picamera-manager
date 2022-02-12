from src.types import Boxes, Box


def test_remove_subboxes():
    # b2 is fully enclosed by b1 - b2 should be removed
    b1 = Box(0, 0, 50, 50)
    b2 = Box(1, 1, 49, 49)

    boxes = Boxes([b1, b2])
    assert len(boxes) == 2

    boxes.remove_subboxes()

    assert len(boxes) == 1

    for box in boxes:
        assert box == b1


def test_remove_subboxes2():
    # b1 and b2 overlap - both should remain
    b1 = Box(0, 0, 50, 50)
    b2 = Box(1, 1, 51, 51)

    boxes = Boxes([b1, b2])
    assert len(boxes) == 2

    boxes.remove_subboxes()

    assert len(boxes) == 2

    for box in boxes:
        assert box == b1 or box == b2


def test_remove_subboxes3():
    # b1 and b2 border eachother - both should remain
    b1 = Box(0, 0, 50, 50)
    b2 = Box(50, 50, 100, 100)

    boxes = Boxes([b1, b2])
    assert len(boxes) == 2

    boxes.remove_subboxes()

    assert len(boxes) == 2

    for box in boxes:
        assert box == b1 or box == b2


def test_serialise():
    b1 = Box(0, 0, 50, 50)
    b2 = Box(50, 50, 100, 100)

    boxes = Boxes([b1, b2])

    string_repr = boxes.serialise()
    print("\n", string_repr)
