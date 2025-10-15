// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract SimpleStorage {
    uint256 private storedValue;
    address public owner;
    mapping(address => uint256) public balances;
    
    event ValueChanged(uint256 newValue, address changedBy);
    event OwnershipTransferred(address previousOwner, address newOwner);
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this function");
        _;
    }
    
    constructor() {
        owner = msg.sender;
        storedValue = 0;
    }
    
    function store(uint256 value) public {
        storedValue = value;
        emit ValueChanged(value, msg.sender);
    }
    
    function retrieve() public view returns (uint256) {
        return storedValue;
    }
    
    function increment() public {
        storedValue += 1;
        emit ValueChanged(storedValue, msg.sender);
    }
    
    function decrement() public {
        require(storedValue > 0, "Cannot decrement below zero");
        storedValue -= 1;
        emit ValueChanged(storedValue, msg.sender);
    }
    
    function addToBalance(address account, uint256 amount) public onlyOwner {
        balances[account] += amount;
    }
    
    function getBalance(address account) public view returns (uint256) {
        return balances[account];
    }
    
    function transferOwnership(address newOwner) public onlyOwner {
        require(newOwner != address(0), "New owner cannot be zero address");
        address previousOwner = owner;
        owner = newOwner;
        emit OwnershipTransferred(previousOwner, newOwner);
    }
    
    function deposit() public payable {
        balances[msg.sender] += msg.value;
    }
    
    function withdraw(uint256 amount) public {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        balances[msg.sender] -= amount;
        payable(msg.sender).transfer(amount);
    }
    
    function getContractBalance() public view returns (uint256) {
        return address(this).balance;
    }
}