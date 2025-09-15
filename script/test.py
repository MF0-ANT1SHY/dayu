from dayu.ark.tagged_value import TaggedValue

if __name__ == "__main__":
    value = TaggedValue("example_tag", 42)
    print(value)  # Output: TaggedValue(tag='example_tag', value=42)