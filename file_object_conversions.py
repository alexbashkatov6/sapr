def attr_name_from_file_to_object(attr_name: str) -> str:
    if attr_name in ["type", "id"]:
        return attr_name + "_"
    if attr_name == "РЎrossroad":  # РЎrossroad Сrossroad
        # print("CONVERTION 1")
        return "crossroad"
    return attr_name


def attr_name_from_object_to_file(attr_name: str) -> str:
    if attr_name in ["type_", "id_"]:
        return attr_name[:-1]
    # if attr_name == "crossroad":
    #     return "РЎrossroad"
    return attr_name
