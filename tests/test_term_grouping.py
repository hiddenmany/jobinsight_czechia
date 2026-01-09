from tools.whitelist_discovery import group_similar_terms

def test_grouping():
    candidates = ["react js", "reactjs", "react.js", "python", "python3", "next.js", "nextjs"]
    groups = group_similar_terms(candidates)
    
    # Check that react variants are grouped
    # "react.js" should be canonical because it has '.' and ' ' and length
    react_canonical = None
    for k, v in groups.items():
        if "react" in k:
            react_canonical = k
            assert set(v) == {"react.js", "react js", "reactjs"}
            
    # Check nextjs
    next_canonical = None
    for k, v in groups.items():
        if "next" in k:
            next_canonical = k
            assert set(v) == {"next.js", "nextjs"}

    print("Grouping test passed!")
    print(f"Groups: {groups}")

if __name__ == "__main__":
    test_grouping()
